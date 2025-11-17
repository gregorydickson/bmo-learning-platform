# frozen_string_literal: true

FactoryBot.define do
  factory :learner do
    sequence(:email) { |n| "learner#{n}@example.com" }
    name { Faker::Name.name }
    phone { Faker::PhoneNumber.phone_number }
    slack_user_id { "U#{Faker::Alphanumeric.alphanumeric(number: 10).upcase}" }
    preferences { { delivery_channel: 'email', frequency: 'daily' } }
    metadata { { onboarded_at: Time.current, skill_level: 'beginner' } }

    trait :with_lessons do
      transient do
        lessons_count { 3 }
      end

      after(:create) do |learner, evaluator|
        create_list(:lesson, evaluator.lessons_count, learner: learner)
      end
    end

    trait :with_learning_paths do
      transient do
        paths_count { 2 }
      end

      after(:create) do |learner, evaluator|
        create_list(:learning_path, evaluator.paths_count, learner: learner)
      end
    end

    trait :advanced do
      metadata { { skill_level: 'advanced', years_experience: 5 } }
    end

    trait :beginner do
      metadata { { skill_level: 'beginner', years_experience: 0 } }
    end
  end
end
