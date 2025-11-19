---
title: Basecamp Rails Patterns - Campfire
description: Real-world Ruby on Rails patterns from Basecamp's open-source Campfire chat application
topics: rails, ruby, hotwire, turbo, stimulus, activerecord, actioncable, sqlite, patterns
source: https://github.com/basecamp/once-campfire
---

# Basecamp Rails Patterns - Campfire

Comprehensive guide extracted from Campfire open-source codebase. This is a production Rails 7 application built by Basecamp, showcasing modern Rails patterns with Hotwire, real-time features, and pragmatic architectural decisions.

## Table of Contents

- [Models](#models) (26 patterns)
- [Controllers](#controllers) (16 patterns)
- [Frontend (Hotwire)](#frontend) (26 patterns)
- [Infrastructure](#infrastructure) (17 patterns)

**Total: 85 patterns**

## Models

### Current Attributes

Thread-safe global state using ActiveSupport::CurrentAttributes for request-scoped data.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActiveSupport/CurrentAttributes.html)

**Source:** [app/models/current.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/current.rb)

```ruby
class Current < ActiveSupport::CurrentAttributes
  attribute :user, :request

  delegate :host, :protocol, to: :request, prefix: true, allow_nil: true

  def account
    Account.first
  end
end
```

### Concerns for Model Organization

Split complex models into focused concerns for better organization and reusability.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActiveSupport/Concern.html)

**Source:** [app/models/user.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/user.rb)

```ruby
class User < ApplicationRecord
  include Avatar, Bot, Mentionable, Role, Transferable

  has_many :memberships, dependent: :delete_all
  has_many :rooms, through: :memberships
  has_many :reachable_messages, through: :rooms, source: :messages
  has_many :messages, dependent: :destroy, foreign_key: :creator_id

  has_secure_password validations: false

  after_create_commit :grant_membership_to_open_rooms

  scope :active, -> { where(active: true) }
  scope :ordered, -> { order("LOWER(name)") }
  scope :filtered_by, ->(query) { where("name like ?", "%#{query}%") }
end
```

### Single Table Inheritance

Use STI for related types with shared behavior but different implementations.

**Rails Docs:** [Guide](https://guides.rubyonrails.org/association_basics.html#single-table-inheritance-sti)

**Source:** [app/models/room.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/room.rb)

```ruby
class Room < ApplicationRecord
  scope :opens,           -> { where(type: "Rooms::Open") }
  scope :closeds,         -> { where(type: "Rooms::Closed") }
  scope :directs,         -> { where(type: "Rooms::Direct") }
  scope :without_directs, -> { where.not(type: "Rooms::Direct") }

  def open?
    is_a?(Rooms::Open)
  end

  def closed?
    is_a?(Rooms::Closed)
  end

  def direct?
    is_a?(Rooms::Direct)
  end
end
```

### STI Singleton Pattern

Use find_or_create for unique resource patterns within STI subclasses.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActiveRecord/Relation.html#method-i-find_or_create_by)

**Source:** [app/models/rooms/direct.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/rooms/direct.rb)

```ruby
class Rooms::Direct < Room
  class << self
    def find_or_create_for(users)
      find_for(users) || create_for({}, users: users)
    end

    private
      def find_for(users)
        all.joins(:users).detect do |room|
          Set.new(room.user_ids) == Set.new(users.pluck(:id))
        end
      end
  end

  def default_involvement
    "everything"
  end
end
```

### STI Auto-Grant Behavior

Override STI subclass with automatic membership grants when type changes.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActiveRecord/Callbacks.html)

**Source:** [app/models/rooms/open.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/rooms/open.rb)

```ruby
class Rooms::Open < Room
  after_save_commit :grant_access_to_all_users

  private
    def grant_access_to_all_users
      memberships.grant_to(User.active) if type_previously_changed?(to: "Rooms::Open")
    end
end

# Automatically grants access to all users when room becomes "open"
```

### Association Extensions

Add custom methods directly to associations for domain-specific operations.

**Rails Docs:** [Guide](https://guides.rubyonrails.org/association_basics.html#association-extensions)

**Source:** [app/models/room.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/room.rb)

```ruby
has_many :memberships, dependent: :delete_all do
  def grant_to(users)
    room = proxy_association.owner
    Membership.insert_all(Array(users).collect { |user|
      { room_id: room.id, user_id: user.id, involvement: room.default_involvement }
    })
  end

  def revoke_from(users)
    destroy_by user: users
  end

  def revise(granted: [], revoked: [])
    transaction do
      grant_to(granted) if granted.present?
      revoke_from(revoked) if revoked.present?
    end
  end
end
```

### Default Associations

Set sensible defaults for belongs_to associations using Current attributes.

**Rails Docs:** [Guide](https://guides.rubyonrails.org/association_basics.html#options-for-belongs-to)

**Source:** [app/models/message.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/message.rb)

```ruby
class Message < ApplicationRecord
  include Attachment, Broadcasts, Mentionee, Pagination, Searchable

  belongs_to :room, touch: true
  belongs_to :creator, class_name: "User", default: -> { Current.user }

  has_many :boosts, dependent: :destroy
  has_rich_text :body

  before_create -> { self.client_message_id ||= Random.uuid }
  after_create_commit -> { room.receive(self) }

  scope :ordered, -> { order(:created_at) }
  scope :with_creator, -> { preload(creator: :avatar_attachment) }
end
```

### Touch Propagation for Parent Updates

Automatically update parent timestamps when children change using touch option.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActiveRecord/Persistence.html#method-i-touch)

**Source:** [app/models/boost.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/boost.rb)

```ruby
class Boost < ApplicationRecord
  belongs_to :message, touch: true
  belongs_to :booster, class_name: "User", default: -> { Current.user }

  scope :ordered, -> { order(:created_at) }
end

# When boost is created/updated/destroyed, message.updated_at is also updated
# Useful for cache invalidation and conditional GET
```

### Increment with Automatic Touch

Increment counters while updating timestamps for connection tracking.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActiveRecord/Persistence.html#method-i-increment-21)

**Source:** [app/models/membership/connectable.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/membership/connectable.rb)

```ruby
def increment_connections
  connected? ? increment!(:connections, touch: true) : update!(connections: 1)
end

def decrement_connections
  connected? ? decrement!(:connections, touch: true) : update!(connections: 0)
end

# increment!/decrement! with touch: true updates both counter and updated_at
# Useful for concurrent connection counting in real-time features
```

### Cursor-Based Pagination

Implement efficient pagination using cursor-based approach with scopes.

**Rails Docs:** [Guide](https://guides.rubyonrails.org/active_record_querying.html#scopes)

**Source:** [app/models/message/pagination.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/message/pagination.rb)

```ruby
module Message::Pagination
  PAGE_SIZE = 40

  included do
    scope :last_page, -> { ordered.last(PAGE_SIZE) }
    scope :first_page, -> { ordered.first(PAGE_SIZE) }

    scope :before, ->(message) { where("created_at < ?", message.created_at) }
    scope :after, ->(message) { where("created_at > ?", message.created_at) }

    scope :page_before, ->(message) { before(message).last_page }
    scope :page_after, ->(message) { after(message).first_page }
  end

  class_methods do
    def page_around(message)
      page_before(message) + [ message ] + page_after(message)
    end

    def paged?
      count > PAGE_SIZE
    end
  end
end
```

### SQLite FTS5 Full-Text Search

Custom full-text search using SQLite FTS5 with manual index management.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActiveRecord/Callbacks.html)

**Source:** [app/models/message/searchable.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/message/searchable.rb)

```ruby
module Message::Searchable
  included do
    after_create_commit  :create_in_index
    after_update_commit  :update_in_index
    after_destroy_commit :remove_from_index

    scope :search, ->(query) {
      joins("join message_search_index idx on messages.id = idx.rowid")
        .where("idx.body match ?", query).ordered
    }
  end

  private
    def create_in_index
      execute_sql_with_binds "insert into message_search_index(rowid, body) values (?, ?)", id, plain_text_body
    end

    def update_in_index
      execute_sql_with_binds "update message_search_index set body = ? where rowid = ?", plain_text_body, id
    end

    def remove_from_index
      execute_sql_with_binds "delete from message_search_index where rowid = ?", id
    end
end
```

### ActionText Attachable for @Mentions

Make models attachable to rich text content for inline mentions.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActionText/Attachable.html)

**Source:** [app/models/user/mentionable.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/user/mentionable.rb)

```ruby
module User::Mentionable
  include ActionText::Attachable

  def to_attachable_partial_path
    "users/mention"
  end

  def to_trix_content_attachment_partial_path
    "users/mention"
  end

  def attachable_plain_text_representation(caption)
    "@#{name}"
  end
end
```

### Extract Mentionees from Rich Text

Parse ActionText body to find mentioned users from attachables.

**Rails Docs:** [Guide](https://guides.rubyonrails.org/action_text_overview.html)

**Source:** [app/models/message/mentionee.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/message/mentionee.rb)

```ruby
module Message::Mentionee
  def mentionees
    room.users.where(id: mentioned_users.map(&:id))
  end

  private
    def mentioned_users
      if body.body
        body.body.attachables.grep(User).uniq
      else
        []
      end
    end
end
```

### ActiveStorage Attachment Variants

Configure attachment variants and processing for images and videos.

**Rails Docs:** [Guide](https://guides.rubyonrails.org/active_storage_overview.html)

**Source:** [app/models/message/attachment.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/message/attachment.rb)

```ruby
module Message::Attachment
  THUMBNAIL_MAX_WIDTH = 1200
  THUMBNAIL_MAX_HEIGHT = 800

  included do
    has_one_attached :attachment do |attachable|
      attachable.variant :thumb, resize_to_limit: [ THUMBNAIL_MAX_WIDTH, THUMBNAIL_MAX_HEIGHT ]
    end
  end

  module ClassMethods
    def create_with_attachment!(attributes)
      create!(attributes).tap(&:process_attachment)
    end
  end

  def process_attachment
    ensure_attachment_analyzed
    process_attachment_thumbnail
  end

  private
    def process_attachment_thumbnail
      case
      when attachment.video?
        attachment.preview(format: :webp).processed
      when attachment.representable?
        attachment.representation(:thumb).processed
      end
    end
end
```

### Role-Based Authorization in Model

Keep authorization logic close to the domain with role checks in concerns.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActiveRecord/Enum.html)

**Source:** [app/models/user/role.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/user/role.rb)

```ruby
module User::Role
  included do
    enum :role, %i[ member administrator bot ]
  end

  def can_administer?(record = nil)
    administrator? || self == record&.creator || record&.new_record?
  end
end
```

### Bot Authentication Pattern

Implement bot users with token-based authentication and webhook delivery.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActiveRecord/SecureToken.html)

**Source:** [app/models/user/bot.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/user/bot.rb)

```ruby
module User::Bot
  included do
    scope :active_bots, -> { active.where(role: :bot) }
    scope :without_bots, -> { where.not(role: :bot) }
    has_one :webhook, dependent: :delete
  end

  module ClassMethods
    def create_bot!(attributes)
      bot_token = generate_bot_token
      webhook_url = attributes.delete(:webhook_url)

      User.create!(**attributes, bot_token: bot_token, role: :bot).tap do |user|
        user.create_webhook!(url: webhook_url) if webhook_url
      end
    end

    def authenticate_bot(bot_key)
      bot_id, bot_token = bot_key.split("-")
      active_bots.find_by(id: bot_id, bot_token: bot_token)
    end

    def generate_bot_token
      SecureRandom.alphanumeric(12)
    end
  end

  def bot_key
    "#{id}-#{bot_token}"
  end
end
```

### Signed ID Tokens for URLs

Use Rails signed IDs for tamper-proof URL tokens.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActiveRecord/SignedId.html)

**Source:** [app/models/user/avatar.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/user/avatar.rb)

```ruby
module User::Avatar
  included do
    has_one_attached :avatar
  end

  class_methods do
    def from_avatar_token(sid)
      find_signed!(sid, purpose: :avatar)
    end
  end

  def avatar_token
    signed_id(purpose: :avatar)
  end
end
```

### Join Code Generation

Auto-generate secure join codes with formatted separators.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActiveRecord/Callbacks.html)

**Source:** [app/models/account/joinable.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/account/joinable.rb)

```ruby
module Account::Joinable
  included do
    before_create { self.join_code = generate_join_code }
  end

  def reset_join_code
    update! join_code: generate_join_code
  end

  private
    def generate_join_code
      SecureRandom.alphanumeric(12).scan(/.{4}/).join("-")
    end
end
```

### Session with Activity Tracking

Track session activity with automatic refresh rate limiting.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActiveRecord/SecureToken.html)

**Source:** [app/models/session.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/session.rb)

```ruby
class Session < ApplicationRecord
  ACTIVITY_REFRESH_RATE = 1.hour

  has_secure_token
  belongs_to :user

  before_create { self.last_active_at ||= Time.now }

  def self.start!(user_agent:, ip_address:)
    create! user_agent: user_agent, ip_address: ip_address
  end

  def resume(user_agent:, ip_address:)
    if last_active_at.before?(ACTIVITY_REFRESH_RATE.ago)
      update! user_agent: user_agent, ip_address: ip_address, last_active_at: Time.now
    end
  end
end
```

### Connection TTL Tracking

Track real-time connections with TTL-based scopes and reference counting.

**Rails Docs:** [Guide](https://guides.rubyonrails.org/active_record_querying.html#scopes)

**Source:** [app/models/membership/connectable.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/membership/connectable.rb)

```ruby
module Membership::Connectable
  CONNECTION_TTL = 60.seconds

  included do
    scope :connected,    -> { where(connected_at: CONNECTION_TTL.ago..) }
    scope :disconnected, -> { where(connected_at: [ nil, ...CONNECTION_TTL.ago ]) }
  end

  class_methods do
    def disconnect_all
      connected.update_all connected_at: nil, connections: 0, updated_at: Time.current
    end

    def connect(membership, connections)
      where(id: membership.id).update_all(connections: connections, connected_at: Time.current, unread_at: nil)
    end
  end

  def connected?
    connected_at? && connected_at >= CONNECTION_TTL.ago
  end

  def refresh_connection
    increment_connections unless connected?
    touch :connected_at
  end
end
```

### Self-Trimming Recent Searches

Automatically trim old records after creation to maintain a fixed history size.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActiveRecord/Callbacks.html)

**Source:** [app/models/search.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/search.rb)

```ruby
class Search < ApplicationRecord
  belongs_to :user

  after_create :trim_recent_searches

  scope :ordered, -> { order(updated_at: :desc) }

  class << self
    def record(query)
      find_or_create_by(query: query).touch
    end
  end

  private
    def trim_recent_searches
      user.searches.excluding(user.searches.ordered.limit(10)).destroy_all
    end
end
```

### Enum with Prefix

Use enums with prefix option for readable scopes and query methods.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActiveRecord/Enum.html)

**Source:** [app/models/membership.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/membership.rb)

```ruby
class Membership < ApplicationRecord
  include Connectable

  enum :involvement, %w[ invisible nothing mentions everything ].index_by(&:itself), prefix: :involved_in

  scope :visible, -> { where.not(involvement: :invisible) }
  scope :unread,  -> { where.not(unread_at: nil) }

  # Usage: membership.involved_in_everything?
  # Scopes: Membership.involved_in_mentions
end
```

### Content Type Inquiry Pattern

Use String#inquiry for readable type checking with query methods.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/String.html#method-i-inquiry)

**Source:** [app/models/message.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/message.rb)

```ruby
def content_type
  case
  when attachment?    then "attachment"
  when sound.present? then "sound"
  else                     "text"
  end.inquiry
end

def sound
  plain_text_body.match(/\A\/play (?<name>\w+)\z/) do |match|
    Sound.find_by_name match[:name]
  end
end

# Usage: message.content_type.text?
# Usage: message.content_type.sound?
```

### In-Memory Registry Pattern

Define static data with built-in lookup index for fast access.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/Enumerable.html#method-i-index_by)

**Source:** [app/models/sound.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/sound.rb)

```ruby
class Sound
  def self.find_by_name(name)
    INDEX[name]
  end

  def self.names
    INDEX.keys.sort
  end

  attr_reader :name, :asset_path, :image, :text

  def initialize(name:, text: nil, image: nil)
    @name = name
    @asset_path = "#{name}.mp3"
    @image = Image.new(**image) if image
    @text = text
  end

  BUILTIN = [
    new(name: "bell", text: "🔔"),
    new(name: "crickets", text: "hears crickets chirping"),
    new(name: "tada", text: "plays a fanfare 🏏"),
    # ... more sounds
  ]

  INDEX = BUILTIN.index_by(&:name)
end
```

### ActiveModel without Database

Use ActiveModel for validation and callbacks without database backing.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActiveModel/Model.html)

**Source:** [app/models/opengraph/metadata.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/opengraph/metadata.rb)

```ruby
class Opengraph::Metadata
  include ActiveModel::Model
  include ActiveModel::Validations::Callbacks
  include ActionView::Helpers::SanitizeHelper

  ATTRIBUTES = %i[ title url image description ]
  attr_accessor *ATTRIBUTES

  before_validation :sanitize_fields

  validates_presence_of :title, :url, :description
  validate :ensure_valid_image_url

  private
    def sanitize_fields
      self.title = sanitize(strip_tags(title))
      self.description = sanitize(strip_tags(description))
    end

    def ensure_valid_image_url
      if image.present?
        errors.add :image, "url is invalid" unless Opengraph::Location.new(image).valid?
      end
    end
end
```

### Module Table Name Prefix

Organize related models under a namespace with table prefix.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActiveRecord/ModelSchema/ClassMethods.html#method-i-table_name_prefix)

**Source:** [app/models/push.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/push.rb)

```ruby
module Push
  def self.table_name_prefix
    "push_"
  end
end

# Usage: Push::Subscription uses push_subscriptions table
```

## Controllers

### Lean ApplicationController

Use concerns to keep ApplicationController minimal and focused on composition.

**Rails Docs:** [Guide](https://guides.rubyonrails.org/action_controller_overview.html)

**Source:** [app/controllers/application_controller.rb](https://github.com/basecamp/once-campfire/blob/main/app/controllers/application_controller.rb)

```ruby
class ApplicationController < ActionController::Base
  include AllowBrowser, Authentication, Authorization, SetCurrentRequest, SetPlatform, TrackedRoomVisit, VersionHeaders
  include Turbo::Streams::Broadcasts, Turbo::Streams::StreamName
end
```

### Authentication Concern

Centralized authentication with session and bot key support.

**Rails Docs:** [Guide](https://guides.rubyonrails.org/action_controller_overview.html#filters)

**Source:** [app/controllers/concerns/authentication.rb](https://github.com/basecamp/once-campfire/blob/main/app/controllers/concerns/authentication.rb)

```ruby
module Authentication
  extend ActiveSupport::Concern
  include SessionLookup

  included do
    before_action :require_authentication
    before_action :deny_bots
    helper_method :signed_in?

    protect_from_forgery with: :exception, unless: -> { authenticated_by.bot_key? }
  end

  class_methods do
    def allow_unauthenticated_access(**options)
      skip_before_action :require_authentication, **options
    end

    def allow_bot_access(**options)
      skip_before_action :deny_bots, **options
    end

    def require_unauthenticated_access(**options)
      skip_before_action :require_authentication, **options
      before_action :restore_authentication, :redirect_signed_in_user_to_root, **options
    end
  end

  private
    def require_authentication
      restore_authentication || bot_authentication || request_authentication
    end

    def set_authenticated_by(method)
      @authenticated_by = method.to_s.inquiry
    end

    def authenticated_by
      @authenticated_by ||= "".inquiry
    end
end
```

### Session Lookup Extraction

Extract reusable authentication logic into small focused modules.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActionDispatch/Cookies.html)

**Source:** [app/controllers/concerns/authentication/session_lookup.rb](https://github.com/basecamp/once-campfire/blob/main/app/controllers/concerns/authentication/session_lookup.rb)

```ruby
module Authentication::SessionLookup
  def find_session_by_cookie
    if token = cookies.signed[:session_token]
      Session.find_by(token: token)
    end
  end
end
```

### Rate Limiting

Built-in rate limiting with custom response handling.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActionController/RateLimiting.html)

**Source:** [app/controllers/sessions_controller.rb](https://github.com/basecamp/once-campfire/blob/main/app/controllers/sessions_controller.rb)

```ruby
class SessionsController < ApplicationController
  allow_unauthenticated_access only: %i[ new create ]
  rate_limit to: 10, within: 3.minutes, only: :create, with: -> { render_rejection :too_many_requests }

  def create
    if user = User.active.authenticate_by(email_address: params[:email_address], password: params[:password])
      start_new_session_for user
      redirect_to post_authenticating_url
    else
      render_rejection :unauthorized
    end
  end

  def destroy
    remove_push_subscription
    reset_authentication
    redirect_to root_url
  end

  private
    def remove_push_subscription
      if endpoint = params[:push_subscription_endpoint]
        Push::Subscription.destroy_by(endpoint: endpoint, user_id: Current.user.id)
      end
    end
end
```

### Require Unauthenticated Access

Redirect already-authenticated users away from login/signup pages.

**Rails Docs:** [Guide](https://guides.rubyonrails.org/action_controller_overview.html#filters)

**Source:** [app/controllers/users_controller.rb](https://github.com/basecamp/once-campfire/blob/main/app/controllers/users_controller.rb)

```ruby
class UsersController < ApplicationController
  require_unauthenticated_access only: %i[ new create ]

  before_action :verify_join_code, only: %i[ new create ]

  def create
    @user = User.create!(user_params)
    start_new_session_for @user
    redirect_to root_url
  rescue ActiveRecord::RecordNotUnique
    redirect_to new_session_url(email_address: user_params[:email_address])
  end

  private
    def verify_join_code
      head :not_found if Current.account.join_code != params[:join_code]
    end
end
```

### Set Current Request Concern

Automatically populate Current attributes and set default URL options.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActionController/UrlFor.html#method-i-default_url_options)

**Source:** [app/controllers/concerns/set_current_request.rb](https://github.com/basecamp/once-campfire/blob/main/app/controllers/concerns/set_current_request.rb)

```ruby
module SetCurrentRequest
  extend ActiveSupport::Concern

  included do
    before_action do
      Current.request = request
    end
  end

  def default_url_options
    { host: Current.request_host, protocol: Current.request_protocol }.compact_blank
  end
end
```

### Version Headers Concern

Add version information to all responses for debugging and cache busting.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActionDispatch/Response.html)

**Source:** [app/controllers/concerns/version_headers.rb](https://github.com/basecamp/once-campfire/blob/main/app/controllers/concerns/version_headers.rb)

```ruby
module VersionHeaders
  extend ActiveSupport::Concern

  included do
    before_action :set_version_headers
  end

  private
    def set_version_headers
      response.headers["X-Version"] = Rails.application.config.app_version
      response.headers["X-Rev"] = Rails.application.config.git_revision
    end
end
```

### PWA Controller for Service Worker

Dedicated controller for PWA manifest and service worker with stable URLs.

**Rails Docs:** [Guide](https://guides.rubyonrails.org/action_controller_overview.html)

**Source:** [app/controllers/pwa_controller.rb](https://github.com/basecamp/once-campfire/blob/main/app/controllers/pwa_controller.rb)

```ruby
class PwaController < ApplicationController
  allow_unauthenticated_access
  skip_forgery_protection

  # We need a stable URL at the root, so we can't use the regular asset path here.
  def service_worker
  end

  # Need ERB interpolation for paths, so can't use asset path here either.
  def manifest
  end
end

# Routes:
# get "webmanifest"    => "pwa#manifest"
# get "service-worker" => "pwa#service_worker"
```

### Tracked Room Visit

Remember user's last visited room using cookies for better UX.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActionDispatch/Cookies.html)

**Source:** [app/controllers/concerns/tracked_room_visit.rb](https://github.com/basecamp/once-campfire/blob/main/app/controllers/concerns/tracked_room_visit.rb)

```ruby
module TrackedRoomVisit
  extend ActiveSupport::Concern

  included do
    helper_method :last_room_visited
  end

  def remember_last_room_visited
    cookies.permanent[:last_room] = @room.id
  end

  def last_room_visited
    Current.user.rooms.find_by(id: cookies[:last_room]) || default_room
  end

  private
    def default_room
      Current.user.rooms.original
    end
end
```

### Room Scoped Concern

Reusable concern for controllers that operate within a room context.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActiveSupport/Concern.html)

**Source:** [app/controllers/concerns/room_scoped.rb](https://github.com/basecamp/once-campfire/blob/main/app/controllers/concerns/room_scoped.rb)

```ruby
module RoomScoped
  extend ActiveSupport::Concern

  included do
    before_action :set_room
  end

  private
    def set_room
      @membership = Current.user.memberships.find_by!(room_id: params[:room_id])
      @room = @membership.room
    end
end
```

### STI Type Coercion with becomes!

Convert between STI types at runtime for polymorphic editing.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActiveRecord/Persistence.html#method-i-becomes-21)

**Source:** [app/controllers/rooms/opens_controller.rb](https://github.com/basecamp/once-campfire/blob/main/app/controllers/rooms/opens_controller.rb)

```ruby
class Rooms::OpensController < RoomsController
  before_action :force_room_type, only: %i[ edit update ]

  def update
    @room.update! room_params
    broadcast_update_room
    redirect_to room_url(@room)
  end

  private
    # Allows us to edit a closed room and turn it into an open one on saving
    def force_room_type
      @room = @room.becomes!(Rooms::Open)
    end

    def broadcast_update_room
      broadcast_replace_to :rooms, target: [ @room, :list ], partial: "users/sidebars/rooms/shared", locals: { room: @room }
    end
end
```

### Turbo Stream Broadcasting in Controllers

Broadcast changes to all connected clients after CRUD operations.

**Rails Docs:** [Turbo Streams](https://turbo.hotwired.dev/handbook/streams)

**Source:** [app/controllers/messages_controller.rb](https://github.com/basecamp/once-campfire/blob/main/app/controllers/messages_controller.rb)

```ruby
def create
  set_room
  @message = @room.messages.create_with_attachment!(message_params)

  @message.broadcast_create
  deliver_webhooks_to_bots
rescue ActiveRecord::RecordNotFound
  render action: :room_not_found
end

def update
  @message.update!(message_params)

  @message.broadcast_replace_to @room, :messages, target: [ @message, :presentation ], partial: "messages/presentation", attributes: { maintain_scroll: true }
  redirect_to room_message_url(@room, @message)
end

def destroy
  @message.destroy
  @message.broadcast_remove_to @room, :messages
end
```

### Fresh When for Conditional GET

Use HTTP caching for efficient pagination requests.

**Rails Docs:** [API Docs](https://api.rubyonrails.org/classes/ActionController/ConditionalGet.html)

**Source:** [app/controllers/messages_controller.rb](https://github.com/basecamp/once-campfire/blob/main/app/controllers/messages_controller.rb)

```ruby
def index
  @messages = find_paged_messages

  if @messages.any?
    fresh_when @messages
  else
    head :no_content
  end
end

private
  def find_paged_messages
    case
    when params[:before].present?
      @room.messages.with_creator.page_before(@room.messages.find(params[:before]))
    when params[:after].present?
      @room.messages.with_creator.page_after(@room.messages.find(params[:after]))
    else
      @room.messages.with_creator.last_page
    end
  end
```

### Broadcast to User Streams

Broadcast targeted updates to specific user channels.

**Rails Docs:** [Turbo Streams](https://turbo.hotwired.dev/handbook/streams)

**Source:** [app/controllers/rooms/directs_controller.rb](https://github.com/basecamp/once-campfire/blob/main/app/controllers/rooms/directs_controller.rb)

```ruby
def create
  room = Rooms::Direct.find_or_create_for(selected_users)

  broadcast_create_room(room)
  redirect_to room_url(room)
end

private
  def broadcast_create_room(room)
    room.memberships.each do |membership|
      membership.broadcast_prepend_to membership.user, :rooms, target: :direct_rooms, partial: "users/sidebars/rooms/direct"
    end
  end

  def selected_users
    User.where(id: selected_users_ids.including(Current.user.id))
  end
```

### Search with Query Sanitization

Sanitize search queries by removing non-word characters.

**Rails Docs:** [Guide](https://guides.rubyonrails.org/action_controller_overview.html)

**Source:** [app/controllers/searches_controller.rb](https://github.com/basecamp/once-campfire/blob/main/app/controllers/searches_controller.rb)

```ruby
class SearchesController < ApplicationController
  before_action :set_messages

  def index
    @query = query if query.present?
    @recent_searches = Current.user.searches.ordered
    @return_to_room = last_room_visited
  end

  def create
    Current.user.searches.record(query)
    redirect_to searches_url(q: query)
  end

  private
    def set_messages
      if query.present?
        @messages = Current.user.reachable_messages.search(query).last(100)
      else
        @messages = Message.none
      end
    end

    def query
      params[:q]&.gsub(/[^[:word:]]/, " ")
    end
end
```

### JSON API with Fallback

Return JSON or no content based on validation results.

**Rails Docs:** [Guide](https://guides.rubyonrails.org/layouts_and_rendering.html)

**Source:** [app/controllers/unfurl_links_controller.rb](https://github.com/basecamp/once-campfire/blob/main/app/controllers/unfurl_links_controller.rb)

```ruby
class UnfurlLinksController < ApplicationController
  def create
    opengraph = Opengraph::Metadata.from_url(url_param)

    if opengraph.valid?
      render json: opengraph
    else
      head :no_content
    end
  end

  private
    def url_param
      params.require(:url)
    end
end
```

## Frontend (Hotwire)

### Turbo Stream Append

Append new content to existing DOM containers with Turbo Streams.

**Rails Docs:** [Turbo Streams](https://turbo.hotwired.dev/handbook/streams)

**Source:** [app/views/messages/create.turbo_stream.erb](https://github.com/basecamp/once-campfire/blob/main/app/views/messages/create.turbo_stream.erb)

```ruby
<%= turbo_stream.append dom_id(@message.room, :messages), @message %>
```

### Model Broadcast Concern

Encapsulate broadcasting logic in model concerns.

**Rails Docs:** [Turbo Streams](https://turbo.hotwired.dev/handbook/streams)

**Source:** [app/models/message/broadcasts.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/message/broadcasts.rb)

```ruby
module Message::Broadcasts
  def broadcast_create
    broadcast_append_to room, :messages, target: [ room, :messages ]
    ActionCable.server.broadcast("unread_rooms", { roomId: room.id })
  end
end
```

### Stimulus Controller with Outlets

Connect Stimulus controllers using outlets for cross-controller communication.

**Rails Docs:** [Stimulus Outlets](https://stimulus.hotwired.dev/reference/outlets)

**Source:** [app/javascript/controllers/composer_controller.js](https://github.com/basecamp/once-campfire/blob/main/app/javascript/controllers/composer_controller.js)

```ruby
export default class extends Controller {
  static classes = ["toolbar"]
  static targets = [ "clientid", "fields", "fileList", "text" ]
  static values = { roomId: Number }
  static outlets = [ "messages" ]

  async #submitMessage() {
    if (this.#validInput()) {
      const clientMessageId = this.#generateClientId()

      await this.messagesOutlet.insertPendingMessage(clientMessageId, this.textTarget)
      await nextFrame()

      this.clientidTarget.value = clientMessageId
      this.element.requestSubmit()
      this.#reset()
    }
  }

  submitByKeyboard(event) {
    const metaEnter = event.key == "Enter" && (event.metaKey || event.ctrlKey)
    const plainEnter = event.keyCode == 13 && !event.shiftKey && !event.isComposing

    if (!this.#usingTouchDevice && (metaEnter || plainEnter)) {
      this.submit(event)
    }
  }
}
```

### File Upload with Progress

Handle file uploads with XMLHttpRequest for progress tracking.

**Rails Docs:** [CSRF Guide](https://guides.rubyonrails.org/security.html#csrf-countermeasures)

**Source:** [app/javascript/models/file_uploader.js](https://github.com/basecamp/once-campfire/blob/main/app/javascript/models/file_uploader.js)

```ruby
export default class FileUploader {
  constructor(file, url, clientMessageId, progressCallback) {
    this.file = file
    this.url = url
    this.clientMessageId = clientMessageId
    this.progressCallback = progressCallback
  }

  upload() {
    const formdata = new FormData()
    formdata.append("message[attachment]", this.file)
    formdata.append("message[client_message_id]", this.clientMessageId)

    const req = new XMLHttpRequest()
    req.open("POST", this.url)
    req.setRequestHeader("X-CSRF-Token", document.querySelector("meta[name=csrf-token]").content)
    req.upload.addEventListener("progress", this.#uploadProgress.bind(this))

    const result = new Promise((resolve, reject) => {
      req.addEventListener("readystatechange", () => {
        if (req.readyState === XMLHttpRequest.DONE) {
          req.status < 400 ? resolve(req.response) : reject()
        }
      })
    })

    req.send(formdata)
    return result
  }

  #uploadProgress(event) {
    if (event.lengthComputable) {
      const percent = Math.round((event.loaded / event.total) * 100)
      this.progressCallback(percent, this.clientMessageId, this.file)
    }
  }
}
```

### Client Message Optimistic Rendering

Render optimistic UI for messages before server confirmation using templates.

**Rails Docs:** [Stimulus](https://stimulus.hotwired.dev/handbook/introduction)

**Source:** [app/javascript/models/client_message.js](https://github.com/basecamp/once-campfire/blob/main/app/javascript/models/client_message.js)

```ruby
const EMOJI_MATCHER = /^(\p{Emoji_Presentation}|\p{Extended_Pictographic}|\uFE0F)+$/gu

export default class ClientMessage {
  #template

  constructor(template) {
    this.#template = template
  }

  render(clientMessageId, node) {
    const now = new Date()
    const body = this.#contentFromNode(node)

    return this.#createFromTemplate({
      clientMessageId,
      body,
      messageTimestamp: Math.floor(now.getTime()),
      messageDatetime: now.toISOString(),
      messageClasses: this.#containsOnlyEmoji(node.textContent) ? "message--emoji" : "",
    })
  }

  update(clientMessageId, body) {
    const element = this.#findWithId(clientMessageId).querySelector(".message__body-content")
    if (element) element.innerHTML = body
  }

  failed(clientMessageId) {
    const element = this.#findWithId(clientMessageId)
    if (element) element.classList.add("message--failed")
  }

  #createFromTemplate(data) {
    let html = this.#template.innerHTML
    for (const key in data) {
      html = html.replaceAll(`$${key}$`, data[key])
    }
    return html
  }

  #containsOnlyEmoji(text) {
    return text?.match(EMOJI_MATCHER)
  }
}
```

### Message Formatting with Threading

Format messages with threading, mention highlighting, and day separators.

**Rails Docs:** [Stimulus](https://stimulus.hotwired.dev/handbook/introduction)

**Source:** [app/javascript/models/message_formatter.js](https://github.com/basecamp/once-campfire/blob/main/app/javascript/models/message_formatter.js)

```ruby
const THREADING_TIME_WINDOW_MILLISECONDS = 5 * 60 * 1000 // 5 minutes

export default class MessageFormatter {
  #userId
  #classes
  #dateFormatter = new Intl.DateTimeFormat(undefined, { dateStyle: "short" })

  constructor(userId, classes) {
    this.#userId = userId
    this.#classes = classes
  }

  format(message, threadstyle) {
    this.#setMeClass(message)
    this.#highlightMentions(message)
    this.#threadMessage(message)
    this.#setFirstOfDayClass(message)
    this.#makeVisible(message)
  }

  #threadMessage(message) {
    if (message.previousElementSibling) {
      const isSameUser = message.previousElementSibling.dataset.userId == message.dataset.userId
      const previousMessageIsRecent = this.#previousMessageIsRecent(message)

      message.classList.toggle(this.#classes.threaded, isSameUser && previousMessageIsRecent)
    }
  }

  #previousMessageIsRecent(message) {
    const previousTimestamp = message.previousElementSibling.dataset.messageTimestamp
    const threadTimestamp = message.dataset.messageTimestamp
    return Math.abs(previousTimestamp - threadTimestamp) <= THREADING_TIME_WINDOW_MILLISECONDS
  }

  #highlightMentions(message) {
    const mentionsCurrentUser = message.querySelector(`.mention img[src^="/users/${Current.user.id}/avatar"]`) !== null
    message.classList.toggle(this.#classes.mentioned, mentionsCurrentUser)
  }
}
```

### Cookie Management Helpers

Simple utilities for getting and setting browser cookies.

**Rails Docs:** [Stimulus](https://stimulus.hotwired.dev/handbook/introduction)

**Source:** [app/javascript/lib/cookie.js](https://github.com/basecamp/once-campfire/blob/main/app/javascript/lib/cookie.js)

```ruby
export function getCookie(name) {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop().split(';').shift()
}

export function setCookie(name, value, days = 365) {
  const expires = new Date()
  expires.setTime(expires.getTime() + (days * 24 * 60 * 60 * 1000))
  document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/`
}

// Usage:
// setCookie("notifications_dismissed", "true")
// getCookie("notifications_dismissed")
```

### Drag and Drop Controller

Simple Stimulus controller for file drag and drop with event dispatch.

**Rails Docs:** [Stimulus Controllers](https://stimulus.hotwired.dev/reference/controllers)

**Source:** [app/javascript/controllers/drop_target_controller.js](https://github.com/basecamp/once-campfire/blob/main/app/javascript/controllers/drop_target_controller.js)

```ruby
export default class extends Controller {
  dragenter(event) {
    event.preventDefault()
  }

  dragover(event) {
    event.preventDefault()
    event.dataTransfer.dropEffect = "copy"
  }

  drop(event) {
    event.preventDefault()
    this.dispatch("drop", { detail: { files: event.dataTransfer.files }})
  }
}
```

### Typing Notifications with ActionCable

Real-time typing indicators using ActionCable and Stimulus with throttling.

**Rails Docs:** [ActionCable Guide](https://guides.rubyonrails.org/action_cable_overview.html)

**Source:** [app/javascript/controllers/typing_notifications_controller.js](https://github.com/basecamp/once-campfire/blob/main/app/javascript/controllers/typing_notifications_controller.js)

```ruby
export default class extends Controller {
  static targets = [ "author", "indicator" ]
  static classes = [ "active" ]

  async connect() {
    this.tracker = new TypingTracker(this.#update.bind(this))

    this.channel = await cable.subscribeTo(
      { channel: "TypingNotificationsChannel", room_id: Current.room.id },
      { received: this.#received.bind(this) }
    )
  }

  start({ target }) {
    if (target.value) {
      this.#throttledSend("start")
    } else {
      this.#send("stop")
    }
  }

  #received({ action, user }) {
    if (user.id !== Current.user.id) {
      action === "start" ? this.tracker.add(user.name) : this.tracker.remove(user.name)
    }
  }

  #throttledSend = throttle(action => this.#send(action))
}
```

### Typing Tracker Model

Track multiple typing users with automatic timeout cleanup.

**Rails Docs:** [Stimulus](https://stimulus.hotwired.dev/handbook/introduction)

**Source:** [app/javascript/models/typing_tracker.js](https://github.com/basecamp/once-campfire/blob/main/app/javascript/models/typing_tracker.js)

```ruby
const REFRESH_INTERVAL = 1000
const TYPING_TIMEOUT = 5000

export default class TypingTracker {
  constructor(callback) {
    this.callback = callback
    this.currentlyTyping = {}
    this.timer = setInterval(this.#refresh.bind(this), REFRESH_INTERVAL)
  }

  add(name) {
    this.currentlyTyping[name] = Date.now()
    this.#refresh()
  }

  remove(name) {
    delete this.currentlyTyping[name]
    this.#refresh()
  }

  #refresh() {
    this.#purgeInactive()
    const names = Object.keys(this.currentlyTyping).sort()
    this.callback(names.length > 0 ? `${names.join(", ")}` : null)
  }

  #purgeInactive() {
    const cutoff = Date.now() - TYPING_TIMEOUT
    this.currentlyTyping = Object.fromEntries(
      Object.entries(this.currentlyTyping).filter(([_name, timestamp]) => timestamp > cutoff)
    )
  }
}
```

### Presence Tracking with Visibility API

Track user presence using Page Visibility API and periodic heartbeats.

**Rails Docs:** [Stimulus Handbook](https://stimulus.hotwired.dev/handbook/introduction)

**Source:** [app/javascript/controllers/presence_controller.js](https://github.com/basecamp/once-campfire/blob/main/app/javascript/controllers/presence_controller.js)

```ruby
const REFRESH_INTERVAL = 50 * 1000 // 50 seconds
const VISIBILITY_CHANGE_DELAY = 5000 // 5 seconds

export default class extends Controller {
  async connect() {
    this.channel = await cable.subscribeTo({ channel: "PresenceChannel", room_id: Current.room.id }, {
      connected: this.#websocketConnected,
      disconnected: this.#websocketDisconnected
    })
    this.wasVisible = true
    await nextFrame()
    this.dispatch("present", { detail: { roomId: Current.room.id } })
  }

  #visible = async () => {
    await delay(VISIBILITY_CHANGE_DELAY)

    if (this.connected && this.#isVisible && !this.wasVisible) {
      this.channel.send({ action: "present" })
      this.#startRefreshTimer()
      this.wasVisible = true
    }
  }

  #refresh = () => {
    this.channel.send({ action: "refresh" })
  }

  get #isVisible() {
    return document.visibilityState === "visible"
  }
}
```

### Scroll Manager with Autoscroll

Manage scroll position with automatic scrolling and position preservation.

**Rails Docs:** [Stimulus Handbook](https://stimulus.hotwired.dev/handbook/introduction)

**Source:** [app/javascript/models/scroll_manager.js](https://github.com/basecamp/once-campfire/blob/main/app/javascript/models/scroll_manager.js)

```ruby
const AUTO_SCROLL_THRESHOLD = 100

export default class ScrollManager {
  static #pendingOperations = Promise.resolve()

  constructor(container) {
    this.#container = container
  }

  async autoscroll(forceScroll, render = () => {}) {
    return this.#appendOperation(async () => {
      const wasNearEnd = this.#scrolledNearEnd

      await render()

      if (wasNearEnd || forceScroll) {
        this.#container.scrollTop = this.#container.scrollHeight
        return true
      } else {
        return false
      }
    })
  }

  async keepScroll(top, render) {
    return this.#appendOperation(async () => {
      const scrollTop = this.#container.scrollTop
      const scrollHeight = this.#container.scrollHeight

      await render()

      if (top) {
        this.#container.scrollTop = scrollTop + (this.#container.scrollHeight - scrollHeight)
      } else {
        this.#container.scrollTop = scrollTop
      }
    })
  }

  get #scrolledNearEnd() {
    return this.#distanceScrolledFromEnd <= AUTO_SCROLL_THRESHOLD
  }
}
```

### IntersectionObserver Pagination

Use IntersectionObserver for infinite scroll pagination.

**Rails Docs:** [Stimulus Handbook](https://stimulus.hotwired.dev/handbook/introduction)

**Source:** [app/javascript/models/message_paginator.js](https://github.com/basecamp/once-campfire/blob/main/app/javascript/models/message_paginator.js)

```ruby
class ScrollTracker {
  constructor(container, callback) {
    this.#container = container
    this.#callback = callback
    this.#intersectionObserver = new IntersectionObserver(this.#handleIntersection.bind(this), { root: container })
    this.#mutationObserver = new MutationObserver(this.#childrenChanged.bind(this))

    this.#mutationObserver.observe(container, { childList: true })
  }

  #handleIntersection(entries) {
    for (const entry of entries) {
      const isFirst = entry.target === this.#container.firstElementChild
      const significantReveal = (isFirst && this.#firstChildWasHidden) || !isFirst

      if (entry.isIntersecting && significantReveal) {
        this.#callback(entry.target)
      }
    }
  }
}

export default class MessagePaginator {
  async #addPage(params, top) {
    const resp = await this.#fetchPage(params)

    if (resp.statusCode === 200) {
      const page = await this.#formatPage(resp)
      keepScroll(this.#container, top, () => insertHTMLFragment(page, this.#container, top))
      this.trimExcessMessages(!top)
    }
  }
}
```

### Autocomplete with Debouncing

Implement autocomplete with debounced search and handler abstraction.

**Rails Docs:** [Stimulus Controllers Reference](https://stimulus.hotwired.dev/reference/controllers)

**Source:** [app/javascript/controllers/autocomplete_controller.js](https://github.com/basecamp/once-campfire/blob/main/app/javascript/controllers/autocomplete_controller.js)

```ruby
export default class extends Controller {
  static targets = [ "select", "input" ]
  static values = { url: String }

  initialize() {
    this.search = debounce(this.search.bind(this), 300)
  }

  connect() {
    this.#installHandler()
    this.inputTarget.focus()
  }

  search(event) {
    this.#handler.search(event.target.value)
  }

  didPressKey(event) {
    if (event.key == "Backspace" && this.inputTarget.value == "") {
      this.#handler.removeLastSelection()
    }
  }

  #installHandler() {
    this.#handler = new AutocompleteHandler(this.inputTarget, this.selectTarget, this.urlValue)
  }
}
```

### JavaScript Timing Helpers

Utility functions for throttle, debounce, and async timing.

**Rails Docs:** [Stimulus Handbook](https://stimulus.hotwired.dev/handbook/introduction)

**Source:** [app/javascript/helpers/timing_helpers.js](https://github.com/basecamp/once-campfire/blob/main/app/javascript/helpers/timing_helpers.js)

```ruby
export function throttle(fn, delay = 1000) {
  let timeoutId = null

  return (...args) => {
    if (!timeoutId) {
      fn(...args)
      timeoutId = setTimeout(() => timeoutId = null, delay)
    }
  }
}

export function debounce(fn, delay = 1000) {
  let timeoutId = null

  return (...args) => {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => fn.apply(this, args), delay)
  }
}

export function nextFrame() {
  return new Promise(requestAnimationFrame)
}

export function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

export function onNextEventLoopTick(callback) {
  setTimeout(callback, 0)
}
```

### DOM Helper Functions

Reusable DOM manipulation utilities for scroll preservation and HTML parsing.

**Rails Docs:** [Stimulus Handbook](https://stimulus.hotwired.dev/handbook/introduction)

**Source:** [app/javascript/helpers/dom_helpers.js](https://github.com/basecamp/once-campfire/blob/main/app/javascript/helpers/dom_helpers.js)

```ruby
export function escapeHTML(html) {
  const div = document.createElement("div")
  div.textContent = html
  return div.innerHTML
}

export function parseHTMLFragment(html) {
  const template = document.createElement("template")
  template.innerHTML = html
  return template.content
}

export async function keepScroll(container, top, fn) {
  pauseInertiaScroll(container)

  const scrollTop = container.scrollTop
  const scrollHeight = container.scrollHeight

  await fn()

  if (top) {
    container.scrollTop = scrollTop + (container.scrollHeight - scrollHeight)
  } else {
    container.scrollTop = scrollTop
  }
}

export function ignoringBriefDisconnects(element, fn) {
  requestAnimationFrame(() => {
    if (!element.isConnected) fn()
  })
}
```

### Stimulus Lifecycle Callbacks

Use target connected/disconnected callbacks for reactive behavior.

**Rails Docs:** [Stimulus Lifecycle Callbacks](https://stimulus.hotwired.dev/reference/lifecycle-callbacks)

**Source:** [app/javascript/controllers/messages_controller.js](https://github.com/basecamp/once-campfire/blob/main/app/javascript/controllers/messages_controller.js)

```ruby
export default class extends Controller {
  static targets = [ "latest", "message", "body", "messages", "template" ]
  static classes = [ "firstOfDay", "formatted", "me", "mentioned", "threaded" ]

  messageTargetConnected(target) {
    this.#formatter.format(target, ThreadStyle.thread)
  }

  bodyTargetConnected(target) {
    this.#formatter.formatBody(target)
  }

  async editMyLastMessage() {
    const editorEmpty = document.querySelector("#composer trix-editor").matches(":empty")

    if (editorEmpty && this.#paginator.upToDate) {
      this.#myLastMessage?.querySelector(".message__edit-btn")?.click()
    }
  }
}
```

### Custom Turbo Stream Actions

Intercept and customize Turbo Stream rendering behavior.

**Rails Docs:** [Turbo Streams Handbook](https://turbo.hotwired.dev/handbook/streams)

**Source:** [app/javascript/controllers/messages_controller.js](https://github.com/basecamp/once-campfire/blob/main/app/javascript/controllers/messages_controller.js)

```ruby
async beforeStreamRender(event) {
  const target = event.detail.newStream.getAttribute("target")

  if (target === this.messagesTarget.id) {
    const render = event.detail.render

    event.detail.render = async (streamElement) => {
      const didScroll = await this.#scrollManager.autoscroll(false, async () => {
        await render(streamElement)
        await nextEventLoopTick()

        this.#positionLastMessage()
        this.#playSoundForLastMessage()
        this.#paginator.trimExcessMessages(true)
      })
      if (!didScroll) {
        this.latestTarget.hidden = false
      }
    }
  }
}
```

### Maintain Scroll on Stream Render

Preserve scroll position when Turbo Streams update content.

**Rails Docs:** [Turbo Streams Handbook](https://turbo.hotwired.dev/handbook/streams)

**Source:** [app/javascript/controllers/maintain_scroll_controller.js](https://github.com/basecamp/once-campfire/blob/main/app/javascript/controllers/maintain_scroll_controller.js)

```ruby
export default class extends Controller {
  #scrollManager

  connect() {
    this.#scrollManager = new ScrollManager(this.element)
  }

  beforeStreamRender(event) {
    const shouldKeepScroll = event.detail.newStream.hasAttribute("maintain_scroll")
    const render = event.detail.render
    const target = event.detail.newStream.getAttribute("target")
    const targetElement = document.getElementById(target)

    if (this.element.contains(targetElement) && shouldKeepScroll) {
      const top = this.#isAboveFold(targetElement)
      event.detail.render = async (streamElement) => {
        this.#scrollManager.keepScroll(top, () => render(streamElement))
      }
    }
  }

  #isAboveFold(element) {
    return element.getBoundingClientRect().top < this.element.clientHeight
  }
}
```

### Turbo Streaming Unsubscribe

Unsubscribe containers from Turbo Stream updates to prevent race conditions.

**Rails Docs:** [Turbo Streams Handbook](https://turbo.hotwired.dev/handbook/streams)

**Source:** [app/javascript/controllers/turbo_streaming_controller.js](https://github.com/basecamp/once-campfire/blob/main/app/javascript/controllers/turbo_streaming_controller.js)

```ruby
export default class extends Controller {
  static targets = [ "container" ]

  unsubscribe() {
    this.containerTarget.removeAttribute("id")
  }
}
```

### Toggle Class Controller

Simple reusable controller for toggling CSS classes.

**Rails Docs:** [Stimulus CSS Classes](https://stimulus.hotwired.dev/reference/css-classes)

**Source:** [app/javascript/controllers/toggle_class_controller.js](https://github.com/basecamp/once-campfire/blob/main/app/javascript/controllers/toggle_class_controller.js)

```ruby
export default class extends Controller {
  static classes = [ "toggle" ]

  toggle() {
    this.element.classList.toggle(this.toggleClass)
  }
}
```

### Web Push Notification Setup

Service worker registration and push subscription management.

**Rails Docs:** [Stimulus Values](https://stimulus.hotwired.dev/reference/values)

**Source:** [app/javascript/controllers/notifications_controller.js](https://github.com/basecamp/once-campfire/blob/main/app/javascript/controllers/notifications_controller.js)

```ruby
export default class extends Controller {
  static values = { subscriptionsUrl: String }

  async attemptToSubscribe() {
    if (this.#allowed) {
      const registration = await this.#serviceWorkerRegistration || await this.#registerServiceWorker()

      switch(Notification.permission) {
        case "denied":  { this.#revealNotAllowedNotice(); break }
        case "granted": { this.#subscribe(registration); break }
        case "default": { this.#requestPermissionAndSubscribe(registration) }
      }
    }
  }

  async #subscribe(registration) {
    registration.pushManager
      .subscribe({ userVisibleOnly: true, applicationServerKey: this.#vapidPublicKey })
      .then(subscription => {
        this.#syncPushSubscription(subscription)
        this.dispatch("ready")
      })
  }

  get #vapidPublicKey() {
    const encodedVapidPublicKey = document.querySelector('meta[name="vapid-public-key"]').content
    return this.#urlBase64ToUint8Array(encodedVapidPublicKey)
  }

  #registerServiceWorker() {
    return navigator.serviceWorker.register("/service-worker.js")
  }
}
```

### ActionCable Channel with Authorization

Reject unauthorized subscriptions in ActionCable channels.

**Rails Docs:** [Action Cable Channels Guide](https://guides.rubyonrails.org/action_cable_overview.html#channels)

**Source:** [app/channels/room_channel.rb](https://github.com/basecamp/once-campfire/blob/main/app/channels/room_channel.rb)

```ruby
class RoomChannel < ApplicationCable::Channel
  def subscribed
    if @room = find_room
      stream_for @room
    else
      reject
    end
  end

  private
    def find_room
      current_user.rooms.find_by(id: params[:room_id])
    end
end
```

### ActionCable Connection Authentication

Authenticate WebSocket connections using existing session infrastructure.

**Rails Docs:** [Action Cable Connection Setup](https://guides.rubyonrails.org/action_cable_overview.html#connection-setup)

**Source:** [app/channels/application_cable/connection.rb](https://github.com/basecamp/once-campfire/blob/main/app/channels/application_cable/connection.rb)

```ruby
module ApplicationCable
  class Connection < ActionCable::Connection::Base
    include Authentication::SessionLookup

    identified_by :current_user

    def connect
      self.current_user = find_verified_user
    end

    private
      def find_verified_user
        if verified_session = find_session_by_cookie
          verified_session.user
        else
          reject_unauthorized_connection
        end
      end
  end
end
```

### Channel with Server-Side Actions

Handle client actions in ActionCable channels and broadcast responses.

**Rails Docs:** [Action Cable Broadcasting](https://guides.rubyonrails.org/action_cable_overview.html#broadcasting)

**Source:** [app/channels/typing_notifications_channel.rb](https://github.com/basecamp/once-campfire/blob/main/app/channels/typing_notifications_channel.rb)

```ruby
class TypingNotificationsChannel < RoomChannel
  def start(data)
    broadcast_to @room, action: :start, user: current_user_attributes
  end

  def stop(data)
    broadcast_to @room, action: :stop, user: current_user_attributes
  end

  private
    def current_user_attributes
      current_user.slice(:id, :name)
    end
end
```

### Channel Inheritance with Lifecycle Hooks

Extend channels with lifecycle callbacks for specialized functionality.

**Rails Docs:** [Action Cable Channels Guide](https://guides.rubyonrails.org/action_cable_overview.html#channels)

**Source:** [app/channels/presence_channel.rb](https://github.com/basecamp/once-campfire/blob/main/app/channels/presence_channel.rb)

```ruby
class PresenceChannel < RoomChannel
  on_subscribe   :present, unless: :subscription_rejected?
  on_unsubscribe :absent,  unless: :subscription_rejected?

  def present
    membership.present
    broadcast_read_room
  end

  def absent
    membership.disconnected
  end

  def refresh
    membership.refresh_connection
  end

  private
    def broadcast_read_room
      ActionCable.server.broadcast "user_#{current_user.id}_reads", { room_id: membership.room_id }
    end
end
```

## Infrastructure

### Defensive HTTP Fetching

Fetch external URLs with size limits, redirect protection, and SSRF prevention.

**Rails Docs:** [ActiveSupport::NumberHelper](https://api.rubyonrails.org/classes/ActiveSupport/NumberHelper.html)

**Source:** [app/models/opengraph/fetch.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/opengraph/fetch.rb)

```ruby
class Opengraph::Fetch
  MAX_BODY_SIZE = 5.megabytes
  MAX_REDIRECTS = 10

  def fetch_document(url, ip: RestrictedHTTP::PrivateNetworkGuard.resolve(url.host))
    request(url, Net::HTTP::Get, ip: ip) do |response|
      return body_if_acceptable(response)
    end
  end

  private
    def size_restricted_body(response)
      StringIO.new.tap do |body|
        response.read_body do |chunk|
          return nil if body.string.bytesize + chunk.bytesize > MAX_BODY_SIZE
          body << chunk
        end
      end.string
    end

    def response_valid?(response)
      status_valid?(response) && content_type_valid?(response) && content_length_valid?(response)
    end
end
```

### Private Network Guard (SSRF Protection)

Prevent server-side request forgery by blocking private IP addresses.

**Rails Docs:** [Rails Security Guide](https://guides.rubyonrails.org/security.html)

**Source:** [lib/restricted_http/private_network_guard.rb](https://github.com/basecamp/once-campfire/blob/main/lib/restricted_http/private_network_guard.rb)

```ruby
module RestrictedHTTP
  class Violation < StandardError; end

  module PrivateNetworkGuard
    extend self

    LOCAL_IP = IPAddr.new("0.0.0.0/8")

    def resolve(hostname)
      Resolv.getaddress(hostname).tap do |ip|
        raise Violation.new("Attempt to access private IP via #{hostname}") if ip && private_ip?(ip)
      end
    end

    def private_ip?(ip)
      IPAddr.new(ip).then do |ipaddr|
        ipaddr.private? || ipaddr.loopback? || LOCAL_IP.include?(ipaddr)
      end
    rescue IPAddr::InvalidAddressError
      true
    end
  end
end
```

### OpenGraph Document Parser

Parse HTML documents to extract OpenGraph metadata using Nokogiri.

**Rails Docs:** [Nokogiri Documentation](https://nokogiri.org/)

**Source:** [app/models/opengraph/document.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/opengraph/document.rb)

```ruby
class Opengraph::Document
  attr_accessor :html

  def initialize(html)
    @html = Nokogiri::HTML(html)
  end

  def opengraph_attributes
    @opengraph_attributes ||= extract_opengraph_attributes
  end

  private
    def extract_opengraph_attributes
      opengraph_tags = html.xpath("//*/meta[starts-with(@property, \"og:\") or starts-with(@name, \"og:\")]").map do |tag|
        key = tag.key?("property") ? "property" : "name"
        [ tag[key].gsub("og:", "").to_sym, sanitize_content(tag["content"]) ] if tag["content"].present?
      end

      Hash[opengraph_tags.compact].slice(*Opengraph::Metadata::ATTRIBUTES)
    end

    def sanitize_content(content)
      html.meta_encoding ? content : content.encode("UTF-8", "binary", invalid: :replace, undef: :replace, replace: "")
    end
end
```

### Webhook Delivery with Response Handling

Deliver webhooks and process responses (text or attachments) automatically.

**Rails Docs:** [ActiveStorage::Blob API](https://api.rubyonrails.org/classes/ActiveStorage/Blob.html)

**Source:** [app/models/webhook.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/webhook.rb)

```ruby
class Webhook < ApplicationRecord
  ENDPOINT_TIMEOUT = 7.seconds

  def deliver(message)
    post(payload(message)).tap do |response|
      if text = extract_text_from(response)
        receive_text_reply_to(message.room, text: text)
      elsif attachment = extract_attachment_from(response)
        receive_attachment_reply_to(message.room, attachment: attachment)
      end
    end
  rescue Net::OpenTimeout, Net::ReadTimeout
    receive_text_reply_to message.room, text: "Failed to respond within #{ENDPOINT_TIMEOUT} seconds"
  end

  private
    def extract_attachment_from(response)
      if mime_type = Mime::Type.lookup(response.content_type)
        ActiveStorage::Blob.create_and_upload! \
          io: StringIO.new(response.body), filename: "attachment.#{mime_type.symbol}"
      end
    end

    def without_recipient_mentions(body)
      body \
        .gsub(user.attachable_plain_text_representation(nil), "")
        .gsub(/\A\p{Space}+|\p{Space}+\z/, "")
    end
end
```

### Concurrent Thread Pool for Push Notifications

Use concurrent-ruby thread pools for high-throughput push notification delivery.

**Rails Docs:** [concurrent-ruby](https://github.com/ruby-concurrency/concurrent-ruby)

**Source:** [lib/web_push/pool.rb](https://github.com/basecamp/once-campfire/blob/main/lib/web_push/pool.rb)

```ruby
class WebPush::Pool
  def initialize(invalid_subscription_handler:)
    @delivery_pool = Concurrent::ThreadPoolExecutor.new(max_threads: 50, queue_size: 10000)
    @invalidation_pool = Concurrent::FixedThreadPool.new(1)
    @connection = Net::HTTP::Persistent.new(name: "web_push", pool_size: 150)
    @invalid_subscription_handler = invalid_subscription_handler
  end

  def queue(payload, subscriptions)
    subscriptions.find_each do |subscription|
      deliver_later(payload, subscription)
    end
  end

  private
    def deliver_later(payload, subscription)
      notification = subscription.notification(**payload)
      subscription_id = subscription.id

      delivery_pool.post do
        deliver(notification, subscription_id)
      rescue Exception => e
        Rails.logger.error "Error in WebPush::Pool.deliver: #{e.class} #{e.message}"
      end
    rescue Concurrent::RejectedExecutionError
    end

    def deliver(notification, id)
      notification.deliver(connection: connection)
    rescue WebPush::ExpiredSubscription, OpenSSL::OpenSSLError => ex
      invalidate_subscription_later(id) if invalid_subscription_handler
    end
end
```

### Service Objects (Plain Ruby Classes)

Encapsulate complex business logic in plain Ruby service objects.

**Rails Docs:** [Active Record Query Interface](https://guides.rubyonrails.org/active_record_querying.html)

**Source:** [app/models/room/message_pusher.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/room/message_pusher.rb)

```ruby
class Room::MessagePusher
  attr_reader :room, :message

  def initialize(room:, message:)
    @room, @message = room, message
  end

  def push
    build_payload.tap do |payload|
      push_to_users_involved_in_everything(payload)
      push_to_users_involved_in_mentions(payload)
    end
  end

  private
    def build_payload
      room.direct? ? build_direct_payload : build_shared_payload
    end

    def push_subscriptions_for_users_involved_in_everything
      relevant_subscriptions.merge(Membership.involved_in_everything)
    end

    def relevant_subscriptions
      Push::Subscription
        .joins(user: :memberships)
        .merge(Membership.visible.disconnected.where(room: room).where.not(user: message.creator))
    end
end
```

### Background Jobs

Use Active Job for async work, keeping jobs thin with service objects.

**Rails Docs:** [Active Job Basics](https://guides.rubyonrails.org/active_job_basics.html)

**Source:** [app/jobs/room/push_message_job.rb](https://github.com/basecamp/once-campfire/blob/main/app/jobs/room/push_message_job.rb)

```ruby
class Room::PushMessageJob < ApplicationJob
  def perform(room, message)
    Room::MessagePusher.new(room:, message:).push
  end
end
```

### Web Push Pool Initialization

Configure custom infrastructure in initializers with cleanup handlers.

**Rails Docs:** [Rails Initializers Guide](https://guides.rubyonrails.org/configuring.html#using-initializer-files)

**Source:** [config/initializers/web_push.rb](https://github.com/basecamp/once-campfire/blob/main/config/initializers/web_push.rb)

```ruby
Rails.application.configure do
  config.x.web_push_pool = WebPush::Pool.new(
    invalid_subscription_handler: ->(subscription_id) do
      Rails.application.executor.wrap do
        Rails.logger.info "Destroying push subscription: #{subscription_id}"
        Push::Subscription.find_by(id: subscription_id)&.destroy
      end
    end
  )

  at_exit { config.x.web_push_pool.shutdown }
end
```

### Module Prepending for Library Patches

Override third-party library methods using module prepending.

**Rails Docs:** [Ruby Module#prepend](https://ruby-doc.org/core-3.1.0/Module.html#method-i-prepend)

**Source:** [config/initializers/web_push.rb](https://github.com/basecamp/once-campfire/blob/main/config/initializers/web_push.rb)

```ruby
module WebPush::PersistentRequest
  def perform
    if @options[:connection]
      http = @options[:connection]
    else
      http = Net::HTTP.new(uri.host, uri.port, *proxy_options)
      http.use_ssl = true
    end

    req = Net::HTTP::Post.new(uri.request_uri, headers)
    req.body = body

    if http.is_a?(Net::HTTP::Persistent)
      response = http.request uri, req
    else
      resp = http.request(req)
      verify_response(resp)
    end

    resp
  end
end

WebPush::Request.prepend WebPush::PersistentRequest

# Adds persistent HTTP connection support to web-push gem
# Better than monkey patching - preserves original behavior
```

### Auto-Loading Extensions Initializer

Automatically require all Ruby extensions from lib directory.

**Rails Docs:** [Rails Autoloading Guide](https://guides.rubyonrails.org/autoloading_and_reloading_constants.html)

**Source:** [config/initializers/extensions.rb](https://github.com/basecamp/once-campfire/blob/main/config/initializers/extensions.rb)

```ruby
%w[ rails_ext ].each do |extensions_dir|
  Dir["#{Rails.root}/lib/#{extensions_dir}/*"].each { |path|
    require "#{extensions_dir}/#{File.basename(path)}"
  }
end

# Loads all files in lib/rails_ext/ automatically
# Good pattern for organizing String, Array, Hash extensions
```

### Script-Aware ActionCable URL Helper

Handle ActionCable URLs with script name prefix for subdirectory deployments.

**Rails Docs:** [ActionView TagHelper API](https://api.rubyonrails.org/classes/ActionView/Helpers/TagHelper.html)

**Source:** [app/helpers/cable_helper.rb](https://github.com/basecamp/once-campfire/blob/main/app/helpers/cable_helper.rb)

```ruby
module CableHelper
  def script_aware_action_cable_meta_tag
    tag.meta \
      name: "action-cable-url",
      content: Pathname(request.script_name) + Pathname(ActionCable.server.config.mount_path)
  end
end

# Supports deployments where app is mounted at a subdirectory
# e.g., example.com/campfire/ instead of example.com/
```

### Core Extensions in lib/

Organize Ruby extensions in lib directory with auto-loading.

**Rails Docs:** [ActiveSupport Core Extensions](https://api.rubyonrails.org/classes/ActiveSupport/CoreExtensions.html)

**Source:** [lib/rails_ext/string.rb](https://github.com/basecamp/once-campfire/blob/main/lib/rails_ext/string.rb)

```ruby
class String
  def all_emoji?
    self.match? /\A(\p{Emoji_Presentation}|\p{Extended_Pictographic}|\uFE0F)+\z/u
  end
end

# Usage: "😄🤘".all_emoji? # => true
# Usage: "Haha! 😄".all_emoji?  # => false
```

### Version Configuration from Environment

Store app version and git revision in Rails config from environment.

**Rails Docs:** [Rails Custom Configuration](https://guides.rubyonrails.org/configuring.html#custom-configuration)

**Source:** [config/initializers/version.rb](https://github.com/basecamp/once-campfire/blob/main/config/initializers/version.rb)

```ruby
Rails.application.config.app_version = ENV.fetch("APP_VERSION", "0")
Rails.application.config.git_revision = ENV["GIT_REVISION"]
```

### Transactional Cleanup

Group related cleanup operations in a transaction for consistency.

**Rails Docs:** [ActiveRecord Transactions API](https://api.rubyonrails.org/classes/ActiveRecord/Transactions/ClassMethods.html)

**Source:** [app/models/user.rb](https://github.com/basecamp/once-campfire/blob/main/app/models/user.rb)

```ruby
def deactivate
  transaction do
    close_remote_connections

    memberships.without_direct_rooms.delete_all
    push_subscriptions.delete_all
    searches.delete_all
    sessions.delete_all

    update! active: false, email_address: deactived_email_address
  end
end

private
  def deactived_email_address
    email_address&.gsub(/@/, "-deactivated-#{SecureRandom.uuid}@")
  end

  def close_remote_connections(reconnect: false)
    ActionCable.server.remote_connections.where(current_user: self).disconnect reconnect: reconnect
  end
```

### Test Helper Organization

Organize test helpers with parallel testing and fixtures.

**Rails Docs:** [Rails Testing Guide](https://guides.rubyonrails.org/testing.html)

**Source:** [test/test_helper.rb](https://github.com/basecamp/once-campfire/blob/main/test/test_helper.rb)

```ruby
class ActiveSupport::TestCase
  include ActiveJob::TestHelper

  parallelize(workers: :number_of_processors)

  fixtures :all

  include SessionTestHelper, MentionTestHelper, TurboTestHelper

  setup do
    ActionCable.server.pubsub.clear

    Rails.configuration.tap do |config|
      config.x.web_push_pool.shutdown
      config.x.web_push_pool = WebPush::Pool.new \
        invalid_subscription_handler: config.x.web_push_pool.invalid_subscription_handler
    end

    WebMock.disable_net_connect!
  end

  teardown do
    WebMock.reset!
  end
end
```

### Direct Routes for Custom URLs

Use Rails direct routes for clean, parameterized URL helpers.

**Rails Docs:** [Rails Direct Routes API](https://api.rubyonrails.org/classes/ActionDispatch/Routing/Mapper/CustomUrls.html)

**Source:** [config/routes.rb](https://github.com/basecamp/once-campfire/blob/main/config/routes.rb)

```ruby
direct :fresh_account_logo do |options|
  route_for :account_logo, v: Current.account&.updated_at&.to_fs(:number), size: options[:size]
end

direct :fresh_user_avatar do |user, options|
  route_for :user_avatar, user.avatar_token, v: user.updated_at.to_fs(:number)
end

# Custom URL pattern for messages
get "@:message_id", to: "rooms#show", as: :at_message

# Nested scoped defaults
scope defaults: { user_id: "me" } do
  resource :sidebar, only: :show
  resource :profile
  resources :push_subscriptions
end
```

### HTML Layout with Hotwire Setup

Modern Rails layout with Turbo prefetch, view transitions, and PWA support.

**Source:** [app/views/layouts/application.html.erb](https://github.com/basecamp/once-campfire/blob/main/app/views/layouts/application.html.erb)

```ruby
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no, interactive-widget=resizes-content">
  <meta name="view-transition" content="same-origin">
  <meta name="color-scheme" content="light dark">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <%= csrf_meta_tags %>
  <%= csp_meta_tag %>

  <%= tag.meta name: "vapid-public-key", content: Rails.configuration.x.vapid.public_key %>
  <%= tag.meta name: "turbo-prefetch", content: "true" %>

  <%= tag.link rel: "manifest", href: webmanifest_path(format: :json) %>
  <%= stylesheet_link_tag :all, "data-turbo-track": "reload" %>
  <%= javascript_importmap_tags %>
</head>

<body class="<%= body_classes %>" data-controller="local-time lightbox">
  <a href="#main-content" class="skip-navigation btn">Skip to main content</a>
  <% if notice = flash[:notice] || flash[:alert] %>
    <div class="flash" data-controller="element-removal" data-action="animationend->element-removal#remove">
      <span role="alert" aria-atomic="true"><%= notice %></span>
    </div>
  <% end %>
</body>
```
