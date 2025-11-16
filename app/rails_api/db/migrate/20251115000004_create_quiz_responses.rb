class CreateQuizResponses < ActiveRecord::Migration[7.2]
  def change
    create_table :quiz_responses do |t|
      t.references :learner, null: false, foreign_key: true
      t.references :lesson, null: false, foreign_key: true
      t.integer :answer_given, null: false
      t.boolean :correct, null: false
      t.integer :time_taken_seconds
      t.jsonb :metadata, default: {}

      t.timestamps
    end

    add_index :quiz_responses, [:learner_id, :lesson_id], unique: true
  end
end
