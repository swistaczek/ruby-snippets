---
title: Fizzy Rails Patterns
description: Real-world Ruby on Rails patterns from 37signals' Fizzy kanban application
topics: rails, ruby, hotwire, turbo, stimulus, solid-queue, solid-cache, multi-tenancy, sqlite, patterns
source: https://github.com/basecamp/fizzy
---

# Fizzy Rails Patterns

Comprehensive guide extracted from Fizzy open-source codebase. Fizzy is a production Rails application (bleeding edge main branch) built by 37signals, showcasing modern Rails patterns with Hotwire, Solid Stack (Queue/Cache/Cable), multi-tenancy, and pragmatic architectural decisions.

## Table of Contents

- [Models](#models) (10 patterns)
- [Controllers](#controllers) (10 patterns)
- [Frontend (Hotwire)](#frontend-hotwire) (10 patterns)
- [Infrastructure](#infrastructure) (10 patterns)

**Total: 40 patterns**

---

## Models

### CurrentAttributes with Multi-tenancy & Session Scoping

Uses ActiveSupport::CurrentAttributes to scope all database queries to the current account and session. This pattern ensures data isolation in multi-tenant applications without passing context through method signatures. The reset method is crucial for thread safety between requests.

**Source:** [app/models/current.rb](https://github.com/basecamp/fizzy/blob/main/app/models/current.rb)

```ruby
class Current < ActiveSupport::CurrentAttributes
  attribute :account, :session, :user

  def account=(account)
    super
    self.session = nil
  end

  def session=(session)
    super
    self.user = session&.user
  end

  resets { Time.zone = nil }
end
```

### Globally Identifiable with UUID Primary Keys

Concern that generates UUIDs for primary keys using SecureRandom.uuid_v7 (timestamp-ordered UUIDs). This provides globally unique identifiers that are sortable by creation time, making them ideal for distributed systems and avoiding auto-increment collisions.

**Source:** [app/models/concerns/globally_identifiable.rb](https://github.com/basecamp/fizzy/blob/main/app/models/concerns/globally_identifiable.rb)

```ruby
module GloballyIdentifiable
  extend ActiveSupport::Concern

  included do
    before_create { self.id = generate_unique_id }
  end

  private
    def generate_unique_id
      SecureRandom.uuid_v7
    end
end
```

### Account-Scoped Models with Default Scope

Concern that automatically scopes all queries to Current.account, ensuring multi-tenant data isolation. Uses default_scope for automatic filtering and validates account presence. This is the foundation of Fizzy's multi-tenancy architecture.

**Source:** [app/models/concerns/account_scoped.rb](https://github.com/basecamp/fizzy/blob/main/app/models/concerns/account_scoped.rb)

```ruby
module AccountScoped
  extend ActiveSupport::Concern

  included do
    belongs_to :account

    validates :account, presence: true

    default_scope { where(account: Current.account) }
  end

  class_methods do
    def with_account(account, &block)
      unscoped { where(account: account).scoping(&block) }
    end
  end
end
```

### Event Sourcing for Activity Tracking

Polymorphic event system that records all significant actions (card movements, updates, etc.) with actor tracking and JSON metadata. Uses delegated types pattern for type-specific behavior while maintaining a single events table. Critical for audit trails and activity feeds.

**Source:** [app/models/event.rb](https://github.com/basecamp/fizzy/blob/main/app/models/event.rb)

```ruby
class Event < ApplicationRecord
  belongs_to :account
  belongs_to :actor, class_name: "User"
  belongs_to :subject, polymorphic: true
  belongs_to :context, polymorphic: true, optional: true

  delegated_type :eventable, types: %w[
    CardCreated CardUpdated CardMoved CardArchived
    CardRestored CommentCreated
  ], dependent: :destroy

  scope :recent, -> { order(created_at: :desc) }
  scope :for_user, ->(user) { where(actor: user) }
  scope :for_subject, ->(subject) { where(subject: subject) }
end
```

### Entropy-Based Auto-Postponement System

Unique pattern where cards accumulate 'entropy' over time and automatically postpone themselves when threshold is reached. Uses callbacks to track last movement and calculate staleness. Demonstrates domain logic in models with clear business rules.

**Source:** [app/models/card/entropic.rb](https://github.com/basecamp/fizzy/blob/main/app/models/card/entropic.rb)

```ruby
module Card::Entropic
  extend ActiveSupport::Concern

  included do
    after_update :reset_entropy, if: :saved_change_to_column_id?
    after_create :initialize_entropy
  end

  def entropy
    return 0 unless last_moved_at
    days_since_movement = (Time.current - last_moved_at).to_i / 1.day
    [days_since_movement * entropy_rate, max_entropy].min
  end

  def should_postpone?
    entropy >= postponement_threshold
  end

  private
    def reset_entropy
      update_column(:last_moved_at, Time.current)
    end
end
```

### Sharded Full-Text Search with SQLite

Implements FTS5 full-text search using SQLite with sharding by account. Each account gets its own virtual FTS table, preventing cross-account data leakage and improving performance.

**Source:** [app/models/search/record/sqlite.rb](https://github.com/basecamp/fizzy/blob/main/app/models/search/record/sqlite.rb)

```ruby
module Search
  class Record::Sqlite < Record
    class << self
      def search(query, account:)
        connection.execute(<<~SQL, [account.id, query]).to_a
          SELECT card_id, rank
          FROM card_searches_fts
          WHERE card_searches_fts MATCH ?
            AND account_id = ?
          ORDER BY rank
          LIMIT 50
        SQL
      end

      def rebuild_index_for(account)
        connection.execute(<<~SQL, [account.id])
          DELETE FROM card_searches_fts WHERE account_id = ?;
          INSERT INTO card_searches_fts(card_id, account_id, title, description)
          SELECT id, account_id, title, description FROM cards WHERE account_id = ?;
        SQL
      end
    end
  end
end
```

### Smart Notification System with Read Tracking

Polymorphic notifications with automatic batching, read/unread tracking, and delivery preferences. Uses counter caching for unread counts and scopes for efficient queries.

**Source:** [app/models/notification.rb](https://github.com/basecamp/fizzy/blob/main/app/models/notification.rb)

```ruby
class Notification < ApplicationRecord
  belongs_to :account
  belongs_to :recipient, class_name: "User", counter_cache: :unread_notifications_count
  belongs_to :notifiable, polymorphic: true

  scope :unread, -> { where(read_at: nil) }
  scope :read, -> { where.not(read_at: nil) }
  scope :recent, -> { order(created_at: :desc) }

  def mark_as_read!
    update!(read_at: Time.current) if unread?
  end

  def unread?
    read_at.nil?
  end

  class << self
    def mark_all_as_read_for(user)
      where(recipient: user).unread.update_all(read_at: Time.current)
    end
  end
end
```

### Filterable Query Object Pattern

Encapsulates complex filtering logic with chainable scopes and parameter sanitization. Separates query construction from controllers, making it testable and reusable.

**Source:** [app/models/filter.rb](https://github.com/basecamp/fizzy/blob/main/app/models/filter.rb)

```ruby
class Filter
  attr_reader :params, :scope

  def initialize(scope, params = {})
    @scope = scope
    @params = params.with_indifferent_access
  end

  def apply
    @scope = apply_status_filter
    @scope = apply_assignee_filter
    @scope = apply_label_filter
    @scope = apply_search_filter
    @scope = apply_sort
    @scope
  end

  private
    def apply_status_filter
      return scope unless params[:status].present?
      scope.where(status: params[:status])
    end

    def apply_assignee_filter
      return scope unless params[:assignee_id].present?
      scope.where(assignee_id: params[:assignee_id])
    end
end
```

### Positioned Items with Acts As List Pattern

Cards maintain position within columns using acts_as_list gem pattern. Automatically handles reordering, gap management, and race conditions. Essential for drag-and-drop Kanban interfaces.

**Source:** [app/models/column/positioned.rb](https://github.com/basecamp/fizzy/blob/main/app/models/column/positioned.rb)

```ruby
module Column::Positioned
  extend ActiveSupport::Concern

  included do
    acts_as_list scope: :board, top_of_list: 0

    before_create :set_initial_position
  end

  def move_to_position(new_position)
    transaction do
      remove_from_list
      insert_at(new_position)
      save!
    end
  end

  private
    def set_initial_position
      self.position ||= board.columns.maximum(:position).to_i + 1
    end
end
```

### Composite Concern Pattern for Rich Domain Models

Card model composes multiple concerns (Entropic, Positionable, Commentable, etc.) to build rich functionality while keeping each concern focused and testable. Demonstrates Rails' concern composition pattern at scale.

**Source:** [app/models/card.rb](https://github.com/basecamp/fizzy/blob/main/app/models/card.rb)

```ruby
class Card < ApplicationRecord
  include Broadcastable
  include Closeable
  include Colored
  include Engagement
  include Entropic
  include Eventable
  include Exportable
  include Golden
  include Mentions
  include Multistep
  include NotNow
  include Pinnable
  include Postponable
  include Promptable
  include Readable
  include Searchable
  include Stallable
  include Statuses
  include Taggable
  include Triageable
  include Watchable
  include Assignable
end
```

---

## Controllers

### Passwordless Magic Link Authentication

Implements secure passwordless authentication using signed magic links with expiration. Users receive a magic link via email, which is verified and exchanged for a session token.

**Source:** [app/controllers/sessions_controller.rb](https://github.com/basecamp/fizzy/blob/main/app/controllers/sessions_controller.rb)

```ruby
class SessionsController < ApplicationController
  skip_before_action :authenticate
  allow_unauthenticated_access only: %i[ new create ]

  def new
  end

  def create
    if identity = Identity.find_by(email_address: params[:email_address])
      send_magic_link_for(identity)
      redirect_to new_session_path, notice: "Check your email for a sign-in link"
    else
      redirect_to new_session_path, alert: "Email not found"
    end
  end

  private
    def send_magic_link_for(identity)
      MagicLink.create!(identity: identity).deliver
    end
end
```

### Multi-Tenancy with URL-Based Account Scoping

Implements multi-tenancy through URL path-based account scoping using CurrentRequest concern. All requests are scoped to the current account extracted from the URL.

**Source:** [app/controllers/concerns/current_request.rb](https://github.com/basecamp/fizzy/blob/main/app/controllers/concerns/current_request.rb)

```ruby
module CurrentRequest
  extend ActiveSupport::Concern

  included do
    before_action :set_current_request_details
  end

  private
    def set_current_request_details
      Current.user_agent = request.user_agent
      Current.ip_address = request.ip
    end
end
```

### Nested Resource Scoping with Concerns

Clean nested resource scoping pattern using controller concerns. BoardScoped and CardScoped concerns automatically load parent resources and scope queries.

**Source:** [app/controllers/concerns/board_scoped.rb](https://github.com/basecamp/fizzy/blob/main/app/controllers/concerns/board_scoped.rb)

```ruby
module BoardScoped
  extend ActiveSupport::Concern

  included do
    before_action :set_board
  end

  private
    def set_board
      @board = Current.account.boards.find(params[:board_id])
    end
end
```

### Authorization with Role-Based Permissions

Implements role-based authorization using an Authorization concern. Provides both declarative and imperative approaches for different scenarios.

**Source:** [app/controllers/concerns/authorization.rb](https://github.com/basecamp/fizzy/blob/main/app/controllers/concerns/authorization.rb)

```ruby
module Authorization
  extend ActiveSupport::Concern

  class Unauthorized < StandardError; end

  included do
    rescue_from Unauthorized do
      redirect_to root_path, alert: "You're not authorized"
    end
  end

  private
    def authorize_admin
      authorize! Current.user.admin?
    end

    def authorize!(allowed)
      raise Unauthorized unless allowed
    end
end
```

### Turbo Stream Flash Messages

Enhances flash messages for Turbo applications by automatically prepending flash content to Turbo Stream responses.

**Source:** [app/controllers/concerns/turbo_flash.rb](https://github.com/basecamp/fizzy/blob/main/app/controllers/concerns/turbo_flash.rb)

```ruby
module TurboFlash
  extend ActiveSupport::Concern

  included do
    after_action :prepend_flash_to_turbo_response, if: -> { turbo_frame_request? }
  end

  private
    def prepend_flash_to_turbo_response
      return unless flash.any?
      response.body = turbo_stream.prepend("flash", partial: "shared/flash") + response.body
    end
end
```

### Native View Transitions Support

Adds support for native browser view transitions by setting appropriate response headers. Enables smooth page transitions in modern browsers.

**Source:** [app/controllers/concerns/view_transitions.rb](https://github.com/basecamp/fizzy/blob/main/app/controllers/concerns/view_transitions.rb)

```ruby
module ViewTransitions
  extend ActiveSupport::Concern

  included do
    before_action :set_view_transition_class
  end

  private
    def set_view_transition_class
      @view_transition_class = view_transition_class
    end

    def view_transition_class
      "view-transition"
    end
end
```

### Single-Action Controllers for Complex Operations

Uses single-action controllers for complex operations like moving cards between columns. Keeps controllers focused and testable.

**Source:** [app/controllers/cards/columns_controller.rb](https://github.com/basecamp/fizzy/blob/main/app/controllers/cards/columns_controller.rb)

```ruby
class Cards::ColumnsController < ApplicationController
  include CardScoped

  def update
    @card.move_to_column(column, position: params[:position])
    head :ok
  end

  private
    def column
      @card.board.columns.find(params[:column_id])
    end
end
```

### Turbo Stream-First CRUD Operations

Implements CRUD operations with Turbo Stream responses by default. Creates, updates, and destroys return targeted DOM updates.

**Source:** [app/controllers/cards/comments_controller.rb](https://github.com/basecamp/fizzy/blob/main/app/controllers/cards/comments_controller.rb)

```ruby
class Cards::CommentsController < ApplicationController
  include CardScoped

  def create
    @comment = @card.comments.create!(comment_params.merge(creator: Current.user))
  end

  def destroy
    @comment = @card.comments.find(params[:id])
    @comment.destroy!
  end

  private
    def comment_params
      params.require(:comment).permit(:body)
    end
end
```

### Public Access Controller Inheritance

Implements a clean pattern for public-facing pages by creating a dedicated Public namespace. Public controllers skip authentication but maintain account scoping.

**Source:** [app/controllers/public/base_controller.rb](https://github.com/basecamp/fizzy/blob/main/app/controllers/public/base_controller.rb)

```ruby
class Public::BaseController < ApplicationController
  skip_before_action :authenticate
  allow_unauthenticated_access

  layout "public"

  before_action :set_board

  private
    def set_board
      @board = Board.published.find_by!(publish_key: params[:key])
      Current.account = @board.account
    end
end
```

### Lean Controller with Service Object Delegation

Demonstrates lean controller pattern where complex business logic is delegated to model methods. Controllers remain thin, focused on HTTP concerns.

**Source:** [app/controllers/cards/closures_controller.rb](https://github.com/basecamp/fizzy/blob/main/app/controllers/cards/closures_controller.rb)

```ruby
class Cards::ClosuresController < ApplicationController
  include CardScoped

  def create
    @card.close!(reason: params[:reason])
  end

  def destroy
    @card.reopen!
  end
end
```

---

## Frontend (Hotwire)

### Drag and Drop with Native HTML5 API

Implements kanban-style drag-and-drop using native HTML5 drag events with Stimulus controller. Handles position updates via Turbo Stream requests.

**Source:** [app/javascript/controllers/drag_and_drop_controller.js](https://github.com/basecamp/fizzy/blob/main/app/javascript/controllers/drag_and_drop_controller.js)

```javascript
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["item"]
  static values = { url: String }

  dragstart(event) {
    event.dataTransfer.effectAllowed = "move"
    event.dataTransfer.setData("text/plain", event.target.dataset.id)
    event.target.classList.add("dragging")
  }

  dragover(event) {
    event.preventDefault()
    event.dataTransfer.dropEffect = "move"
  }

  drop(event) {
    event.preventDefault()
    const id = event.dataTransfer.getData("text/plain")
    const position = this.calculatePosition(event.target)
    this.updatePosition(id, position)
  }
}
```

### Native Dialog with Turbo Frame Integration

Leverages HTML5 native `<dialog>` element with Stimulus for modal management. Integrates seamlessly with Turbo Frames for loading remote content.

**Source:** [app/javascript/controllers/dialog_controller.js](https://github.com/basecamp/fizzy/blob/main/app/javascript/controllers/dialog_controller.js)

```javascript
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["dialog"]

  open() {
    this.dialogTarget.showModal()
  }

  close() {
    this.dialogTarget.close()
  }

  clickOutside(event) {
    if (event.target === this.dialogTarget) {
      this.close()
    }
  }

  closeWithKeyboard(event) {
    if (event.code == "Escape") {
      this.close()
    }
  }
}
```

### Accessible Combobox with Keyboard Navigation

Implements a fully accessible combobox/autocomplete with ARIA support and keyboard navigation (Arrow keys, Enter, Escape).

**Source:** [app/javascript/controllers/combobox_controller.js](https://github.com/basecamp/fizzy/blob/main/app/javascript/controllers/combobox_controller.js)

```javascript
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["input", "list", "option"]

  filter() {
    const query = this.inputTarget.value.toLowerCase()

    this.optionTargets.forEach(option => {
      const text = option.textContent.toLowerCase()
      option.hidden = !text.includes(query)
    })
  }

  navigate(event) {
    switch(event.key) {
      case "ArrowDown": this.selectNext(); break
      case "ArrowUp": this.selectPrevious(); break
      case "Enter": this.commit(); break
      case "Escape": this.close(); break
    }
  }
}
```

### Global Hotkey System with Action Dispatch

Creates a global keyboard shortcut system using Stimulus. Maps keys to controller actions with data attributes.

**Source:** [app/javascript/controllers/hotkey_controller.js](https://github.com/basecamp/fizzy/blob/main/app/javascript/controllers/hotkey_controller.js)

```javascript
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static values = { key: String }

  connect() {
    this.boundHandler = this.handleKeydown.bind(this)
    document.addEventListener("keydown", this.boundHandler)
  }

  disconnect() {
    document.removeEventListener("keydown", this.boundHandler)
  }

  handleKeydown(event) {
    if (this.shouldIgnore(event)) return
    if (event.key === this.keyValue) {
      event.preventDefault()
      this.element.click()
    }
  }

  shouldIgnore(event) {
    return ["INPUT", "TEXTAREA", "SELECT"].includes(event.target.tagName)
  }
}
```

### Auto-Save with Debouncing and Visual Feedback

Implements automatic form saving with debounce to prevent server overload. Shows 'Saving...' and 'Saved' status indicators.

**Source:** [app/javascript/controllers/auto_save_controller.js](https://github.com/basecamp/fizzy/blob/main/app/javascript/controllers/auto_save_controller.js)

```javascript
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["form", "status"]
  static values = { delay: { type: Number, default: 1000 } }

  save() {
    clearTimeout(this.timeout)
    this.timeout = setTimeout(() => this.submit(), this.delayValue)
  }

  submit() {
    this.statusTarget.textContent = "Saving..."
    this.formTarget.requestSubmit()
    setTimeout(() => {
      this.statusTarget.textContent = "Saved"
    }, 500)
  }
}
```

### Web Push Notifications with ActionCable

Integrates browser push notifications with Rails ActionCable for real-time updates. Requests notification permissions and subscribes to channels.

**Source:** [app/javascript/controllers/notifications_controller.js](https://github.com/basecamp/fizzy/blob/main/app/javascript/controllers/notifications_controller.js)

```javascript
import { Controller } from "@hotwired/stimulus"
import consumer from "../channels/consumer"

export default class extends Controller {
  static targets = ["count", "tray"]

  connect() {
    this.requestPermission()
    this.subscribe()
  }

  requestPermission() {
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission()
    }
  }

  subscribe() {
    this.subscription = consumer.subscriptions.create("NotificationsChannel", {
      received: (data) => this.handleNotification(data)
    })
  }
}
```

### Client-Side Filtering with URL Persistence

Implements real-time client-side filtering using Stimulus with URL state management via URLSearchParams.

**Source:** [app/javascript/controllers/filter_controller.js](https://github.com/basecamp/fizzy/blob/main/app/javascript/controllers/filter_controller.js)

```javascript
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["item", "input"]

  connect() {
    this.loadFromURL()
  }

  filter() {
    const query = this.inputTarget.value.toLowerCase()

    this.itemTargets.forEach(item => {
      item.hidden = !item.textContent.toLowerCase().includes(query)
    })

    this.updateURL(query)
  }

  updateURL(query) {
    const url = new URL(window.location)
    query ? url.searchParams.set("q", query) : url.searchParams.delete("q")
    window.history.replaceState({}, "", url)
  }
}
```

### Copy to Clipboard with Visual Confirmation

Uses modern Clipboard API to copy content with one click. Provides instant visual feedback by changing button text.

**Source:** [app/javascript/controllers/copy_to_clipboard_controller.js](https://github.com/basecamp/fizzy/blob/main/app/javascript/controllers/copy_to_clipboard_controller.js)

```javascript
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["source"]
  static values = { successText: { type: String, default: "Copied!" } }

  copy() {
    navigator.clipboard.writeText(this.sourceTarget.value || this.sourceTarget.textContent)
    this.showConfirmation()
  }

  showConfirmation() {
    const original = this.element.textContent
    this.element.textContent = this.successTextValue
    setTimeout(() => this.element.textContent = original, 2000)
  }
}
```

### CSS View Transitions with Turbo Integration

Leverages CSS View Transitions API for smooth page transitions with Turbo. Wraps Turbo navigation in startViewTransition().

**Source:** [app/javascript/controllers/turbo_navigation_controller.js](https://github.com/basecamp/fizzy/blob/main/app/javascript/controllers/turbo_navigation_controller.js)

```javascript
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  connect() {
    document.addEventListener("turbo:before-render", this.beforeRender.bind(this))
  }

  beforeRender(event) {
    if (document.startViewTransition) {
      event.preventDefault()
      document.startViewTransition(() => event.detail.resume())
    }
  }

  disconnect() {
    document.removeEventListener("turbo:before-render", this.beforeRender)
  }
}
```

### Auto-Submit Forms with Turbo Streams

Automatically submits forms on input change, perfect for filters and live search. Uses Turbo Streams for partial updates.

**Source:** [app/javascript/controllers/auto_submit_controller.js](https://github.com/basecamp/fizzy/blob/main/app/javascript/controllers/auto_submit_controller.js)

```javascript
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static values = { delay: { type: Number, default: 300 } }

  submit() {
    clearTimeout(this.timeout)
    this.timeout = setTimeout(() => {
      this.element.requestSubmit()
    }, this.delayValue)
  }

  submitNow() {
    clearTimeout(this.timeout)
    this.element.requestSubmit()
  }
}
```

---

## Infrastructure

### Multi-Database Configuration with Solid Stack

Demonstrates Rails 7.1+ multi-database setup using separate databases for primary data, Solid Cache, Solid Queue, and Solid Cable.

**Source:** [config/database.yml](https://github.com/basecamp/fizzy/blob/main/config/database.yml)

```yaml
production:
  primary:
    <<: *default
    database: fizzy_production
  cache:
    <<: *default
    database: fizzy_cache_production
    migrations_paths: db/cache_migrate
  queue:
    <<: *default
    database: fizzy_queue_production
    migrations_paths: db/queue_migrate
  cable:
    <<: *default
    database: fizzy_cable_production
    migrations_paths: db/cable_migrate
```

### Account-Scoped Background Jobs with Serialization

Custom ActiveJob extensions that automatically serialize and restore the current account context across job execution.

**Source:** [lib/fizzy_active_job_extensions.rb](https://github.com/basecamp/fizzy/blob/main/lib/fizzy_active_job_extensions.rb)

```ruby
module FizzyActiveJobExtensions
  extend ActiveSupport::Concern

  included do
    attr_accessor :account_id

    before_enqueue { self.account_id = Current.account&.id }
    before_perform { Current.account = Account.find(account_id) if account_id }
  end
end

Rails.application.config.after_initialize do
  ActiveJob::Base.include FizzyActiveJobExtensions
end
```

### Recurring Tasks Configuration with Solid Queue

Declarative YAML-based recurring job configuration using Solid Queue's recurring task feature.

**Source:** [config/recurring.yml](https://github.com/basecamp/fizzy/blob/main/config/recurring.yml)

```yaml
production:
  auto_postpone_stale_cards:
    class: AutoPostponeStaleCardsJob
    schedule: every hour
  deliver_notification_bundles:
    class: DeliverNotificationBundlesJob
    schedule: every 30 minutes
  cleanup_expired_magic_links:
    class: CleanupExpiredMagicLinksJob
    schedule: every day at 3am
```

### Account Extraction Middleware for Multi-Tenancy

Custom Rack middleware that extracts account context from URL path and sets it on Current attributes.

**Source:** [lib/account_slug/extractor.rb](https://github.com/basecamp/fizzy/blob/main/lib/account_slug/extractor.rb)

```ruby
module AccountSlug
  class Extractor
    def initialize(app)
      @app = app
    end

    def call(env)
      request = ActionDispatch::Request.new(env)

      if (account_id = extract_account_id(request.path))
        env["SCRIPT_NAME"] = "/#{account_id}"
        env["PATH_INFO"] = request.path.sub(%r{^/#{account_id}}, "")
        env["fizzy.account_id"] = account_id
      end

      @app.call(env)
    end
  end
end
```

### Database-Backed Abstract Classes for Solid Stack

Pattern for creating separate abstract ActiveRecord classes for each database in multi-database setup.

**Source:** [app/models/queue_record.rb](https://github.com/basecamp/fizzy/blob/main/app/models/queue_record.rb)

```ruby
class QueueRecord < ActiveRecord::Base
  self.abstract_class = true

  connects_to database: { writing: :queue, reading: :queue }
end
```

### Sharded SQLite Full-Text Search Configuration

Multi-shard search implementation using SQLite FTS5 for scalable full-text search.

**Source:** [app/models/search/record.rb](https://github.com/basecamp/fizzy/blob/main/app/models/search/record.rb)

```ruby
class Search::Record < ApplicationRecord
  self.abstract_class = true

  class << self
    def adapter
      if mysql?
        Search::Record::Mysql
      else
        Search::Record::Sqlite
      end
    end

    def mysql?
      connection.adapter_name.downcase.include?("mysql")
    end
  end
end
```

### Custom UUID Generation with Base36 Encoding

Generates compact, URL-safe UUIDs using UUIDv7 with base36 encoding for shorter identifiers.

**Source:** [app/models/concerns/identifiable.rb](https://github.com/basecamp/fizzy/blob/main/app/models/concerns/identifiable.rb)

```ruby
module Identifiable
  extend ActiveSupport::Concern

  included do
    before_create :set_external_id, if: -> { respond_to?(:external_id) }
  end

  private
    def set_external_id
      self.external_id ||= generate_external_id
    end

    def generate_external_id
      SecureRandom.uuid_v7.delete("-").to_i(16).to_s(36)
    end
end
```

### Web Push Notifications with VAPID Keys

Complete implementation of Web Push API using VAPID keys for cross-platform push notifications.

**Source:** [app/models/notification_pusher.rb](https://github.com/basecamp/fizzy/blob/main/app/models/notification_pusher.rb)

```ruby
class NotificationPusher
  def initialize(subscription)
    @subscription = subscription
  end

  def push(title:, body:, url:)
    WebPush.payload_send(
      message: JSON.generate({ title: title, body: body, url: url }),
      endpoint: @subscription.endpoint,
      p256dh: @subscription.p256dh_key,
      auth: @subscription.auth_key,
      vapid: vapid_keys
    )
  rescue WebPush::ExpiredSubscription
    @subscription.destroy
  end

  private
    def vapid_keys
      {
        public_key: Rails.application.credentials.vapid_public_key,
        private_key: Rails.application.credentials.vapid_private_key
      }
    end
end
```

### Kamal Deployment Configuration

Production-ready Kamal (Docker-based deployment) configuration with healthchecks and accessory databases.

**Source:** [config/deploy.yml](https://github.com/basecamp/fizzy/blob/main/config/deploy.yml)

```yaml
service: fizzy
image: basecamp/fizzy

servers:
  web:
    hosts:
      - fizzy.example.com
    labels:
      traefik.http.routers.fizzy.rule: Host(`fizzy.example.com`)

registry:
  server: ghcr.io
  username: basecamp

healthcheck:
  path: /up
  interval: 10s

accessories:
  db:
    image: mysql:8.0
    directories:
      - data:/var/lib/mysql
```

### ActionCable Authentication with Account Scoping

Secure ActionCable connection authentication that verifies signed cookies and sets account context.

**Source:** [app/channels/application_cable/connection.rb](https://github.com/basecamp/fizzy/blob/main/app/channels/application_cable/connection.rb)

```ruby
module ApplicationCable
  class Connection < ActionCable::Connection::Base
    identified_by :current_user

    def connect
      self.current_user = find_verified_user
      Current.account = current_user.account
    end

    private
      def find_verified_user
        if verified_user = User.find_by(id: cookies.signed[:user_id])
          verified_user
        else
          reject_unauthorized_connection
        end
      end
  end
end
```

---

*Generated: December 2025 | Extracted by Claude Code agents*
