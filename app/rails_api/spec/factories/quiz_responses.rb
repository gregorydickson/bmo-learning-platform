# frozen_string_literal: true

FactoryBot.define do
  factory :quiz_response do
    association :lesson
    user_answer { lesson.quiz_options.sample }
    is_correct { user_answer == lesson.quiz_answer }
    time_spent_seconds { rand(30..300) }
    attempts { 1 }

    trait :correct do
      user_answer { lesson.quiz_answer }
      is_correct { true }
    end

    trait :incorrect do
      is_correct { false }
      after(:build) do |response|
        # Ensure answer is wrong
        wrong_answers = response.lesson.quiz_options - [response.lesson.quiz_answer]
        response.user_answer = wrong_answers.sample
      end
    end

    trait :multiple_attempts do
      attempts { rand(2..5) }
    end
  end
end
