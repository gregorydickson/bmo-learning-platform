# frozen_string_literal: true

FactoryBot.define do
  factory :learning_path do
    association :learner
    name { Faker::Lorem.sentence(word_count: 3) }
    description { Faker::Lorem.paragraph }
    topics { [Faker::Lorem.word, Faker::Lorem.word, Faker::Lorem.word] }
    status { 'active' }
    progress { 0.0 }

    trait :completed do
      status { 'completed' }
      progress { 100.0 }
      completed_at { Time.current }
    end

    trait :in_progress do
      status { 'in_progress' }
      progress { 45.0 }
    end
  end
end
