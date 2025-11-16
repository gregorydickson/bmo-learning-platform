class CreateLessons < ActiveRecord::Migration[7.2]
  def change
    create_table :lessons do |t|
      t.references :learning_path, null: false, foreign_key: true
      t.string :topic, null: false
      t.text :content, null: false
      t.jsonb :key_points, default: []
      t.text :scenario
      t.string :quiz_question
      t.jsonb :quiz_options, default: []
      t.integer :correct_answer
      t.datetime :delivered_at
      t.string :delivery_channel
      t.jsonb :metadata, default: {}

      t.timestamps
    end

    add_index :lessons, :delivered_at
  end
end
