# frozen_string_literal: true

class CreateDocuments < ActiveRecord::Migration[7.2]
  def change
    create_table :documents do |t|
      t.string :filename, null: false
      t.string :s3_bucket, null: false
      t.string :s3_key, null: false
      t.string :s3_etag
      t.bigint :size
      t.string :content_type
      t.string :category, default: 'general'
      t.bigint :learner_id
      t.bigint :uploaded_by
      t.boolean :processed, default: false
      t.datetime :processed_at
      t.text :processing_error
      t.jsonb :metadata, default: {}

      t.timestamps
    end

    add_index :documents, :learner_id
    add_index :documents, :category
    add_index :documents, :processed
    add_index :documents, :s3_key, unique: true
    add_index :documents, :created_at
  end
end
