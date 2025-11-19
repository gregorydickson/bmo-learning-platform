# This file is auto-generated from the current state of the database. Instead
# of editing this file, please use the migrations feature of Active Record to
# incrementally modify your database, and then regenerate this schema definition.
#
# This file is the source Rails uses to define your schema when running `bin/rails
# db:schema:load`. When creating a new database, `bin/rails db:schema:load` tends to
# be faster and is potentially less error prone than running all of your
# migrations from scratch. Old migrations may fail to apply correctly if those
# migrations use external dependencies or application code.
#
# It's strongly recommended that you check this file into your version control system.

ActiveRecord::Schema[7.2].define(version: 2025_11_18_000001) do
  # These are extensions that must be enabled in order to support this database
  enable_extension "plpgsql"

  create_table "documents", force: :cascade do |t|
    t.string "filename", null: false
    t.string "s3_bucket", null: false
    t.string "s3_key", null: false
    t.string "s3_etag"
    t.bigint "size"
    t.string "content_type"
    t.string "category", default: "general"
    t.bigint "learner_id"
    t.bigint "uploaded_by"
    t.boolean "processed", default: false
    t.datetime "processed_at"
    t.text "processing_error"
    t.jsonb "metadata", default: {}
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["category"], name: "index_documents_on_category"
    t.index ["created_at"], name: "index_documents_on_created_at"
    t.index ["learner_id"], name: "index_documents_on_learner_id"
    t.index ["processed"], name: "index_documents_on_processed"
    t.index ["s3_key"], name: "index_documents_on_s3_key", unique: true
  end

  create_table "learners", force: :cascade do |t|
    t.string "email", null: false
    t.string "name", null: false
    t.string "phone"
    t.string "slack_user_id"
    t.jsonb "preferences", default: {}
    t.jsonb "metadata", default: {}
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["email"], name: "index_learners_on_email", unique: true
  end

  create_table "learning_paths", force: :cascade do |t|
    t.bigint "learner_id", null: false
    t.string "topic", null: false
    t.string "status", default: "active"
    t.integer "lessons_completed", default: 0
    t.integer "total_lessons", default: 10
    t.jsonb "metadata", default: {}
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["learner_id", "topic"], name: "index_learning_paths_on_learner_id_and_topic", unique: true
    t.index ["learner_id"], name: "index_learning_paths_on_learner_id"
  end

  create_table "lessons", force: :cascade do |t|
    t.bigint "learning_path_id", null: false
    t.string "topic", null: false
    t.text "content", null: false
    t.jsonb "key_points", default: []
    t.text "scenario"
    t.string "quiz_question"
    t.jsonb "quiz_options", default: []
    t.integer "correct_answer"
    t.datetime "delivered_at"
    t.string "delivery_channel"
    t.jsonb "metadata", default: {}
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["delivered_at"], name: "index_lessons_on_delivered_at"
    t.index ["learning_path_id"], name: "index_lessons_on_learning_path_id"
  end

  create_table "quiz_responses", force: :cascade do |t|
    t.bigint "learner_id", null: false
    t.bigint "lesson_id", null: false
    t.integer "answer_given", null: false
    t.boolean "correct", null: false
    t.integer "time_taken_seconds"
    t.jsonb "metadata", default: {}
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["learner_id", "lesson_id"], name: "index_quiz_responses_on_learner_id_and_lesson_id", unique: true
    t.index ["learner_id"], name: "index_quiz_responses_on_learner_id"
    t.index ["lesson_id"], name: "index_quiz_responses_on_lesson_id"
  end

  add_foreign_key "learning_paths", "learners"
  add_foreign_key "lessons", "learning_paths"
  add_foreign_key "quiz_responses", "learners"
  add_foreign_key "quiz_responses", "lessons"
end
