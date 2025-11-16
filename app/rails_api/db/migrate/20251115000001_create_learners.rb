class CreateLearners < ActiveRecord::Migration[7.2]
  def change
    create_table :learners do |t|
      t.string :email, null: false, index: { unique: true }
      t.string :name, null: false
      t.string :phone
      t.string :slack_user_id
      t.jsonb :preferences, default: {}
      t.jsonb :metadata, default: {}

      t.timestamps
    end
  end
end
