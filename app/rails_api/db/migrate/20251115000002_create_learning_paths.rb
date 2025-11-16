class CreateLearningPaths < ActiveRecord::Migration[7.2]
  def change
    create_table :learning_paths do |t|
      t.references :learner, null: false, foreign_key: true
      t.string :topic, null: false
      t.string :status, default: 'active'
      t.integer :lessons_completed, default: 0
      t.integer :total_lessons, default: 10
      t.jsonb :metadata, default: {}

      t.timestamps
    end

    add_index :learning_paths, [:learner_id, :topic], unique: true
  end
end
