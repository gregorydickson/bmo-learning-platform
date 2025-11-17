# frozen_string_literal: true

FactoryBot.define do
  factory :lesson do
    association :learner
    topic { Faker::Lorem.sentence(word_count: 3) }
    content { Faker::Lorem.paragraph(sentence_count: 5) }
    scenario { Faker::Lorem.paragraph(sentence_count: 3) }
    quiz_question { "#{Faker::Lorem.sentence}?" }
    quiz_options { [Faker::Lorem.word, Faker::Lorem.word, Faker::Lorem.word, Faker::Lorem.word] }
    quiz_answer { quiz_options.sample }
    status { 'pending' }
    difficulty { 'medium' }

    trait :completed do
      status { 'completed' }
      completed_at { Time.current }
    end

    trait :in_progress do
      status { 'in_progress' }
      started_at { 1.hour.ago }
    end

    trait :easy do
      difficulty { 'easy' }
    end

    trait :hard do
      difficulty { 'hard' }
    end

    trait :with_quiz_response do
      after(:create) do |lesson|
        create(:quiz_response, lesson: lesson)
      end
    end
  end
end
