# frozen_string_literal: true

require 'rails_helper'

RSpec.describe QuizResponse, type: :model do
  describe 'associations' do
    it { should belong_to(:learner) }
    it { should belong_to(:lesson) }
  end

  describe 'validations' do
    it { should validate_presence_of(:answer_given) }
    it { should validate_inclusion_of(:correct).in_array([true, false]) }
  end

  describe 'factory' do
    it 'has a valid factory' do
      expect(build(:quiz_response)).to be_valid
    end

    it 'creates correct response' do
      response = create(:quiz_response, :correct)
      expect(response.is_correct).to be true
      expect(response.user_answer).to eq(response.lesson.quiz_answer)
    end

    it 'creates incorrect response' do
      response = create(:quiz_response, :incorrect)
      expect(response.is_correct).to be false
      expect(response.user_answer).not_to eq(response.lesson.quiz_answer)
    end
  end

  describe 'callbacks' do
    describe '#update_learning_path_progress' do
      let(:learning_path) { create(:learning_path, total_lessons: 5, lessons_completed: 2) }
      let(:lesson) { create(:lesson, learning_path: learning_path) }

      context 'when answer is correct' do
        it 'increments lessons_completed' do
          expect {
            create(:quiz_response, :correct, lesson: lesson, learner: learning_path.learner)
          }.to change { learning_path.reload.lessons_completed }.by(1)
        end

        it 'does not complete path if not all lessons done' do
          create(:quiz_response, :correct, lesson: lesson, learner: learning_path.learner)
          expect(learning_path.reload.status).to eq('active')
        end

        context 'when completing final lesson' do
          let(:learning_path) { create(:learning_path, total_lessons: 3, lessons_completed: 2) }

          it 'marks learning path as completed' do
            create(:quiz_response, :correct, lesson: lesson, learner: learning_path.learner)
            expect(learning_path.reload.status).to eq('completed')
          end
        end
      end

      context 'when answer is incorrect' do
        it 'does not increment lessons_completed' do
          expect {
            create(:quiz_response, :incorrect, lesson: lesson, learner: learning_path.learner)
          }.not_to change { learning_path.reload.lessons_completed }
        end

        it 'does not complete learning path' do
          create(:quiz_response, :incorrect, lesson: lesson, learner: learning_path.learner)
          expect(learning_path.reload.status).to eq('active')
        end
      end
    end
  end

  describe 'correctness checking' do
    let(:lesson) { create(:lesson, quiz_answer: 'correct_answer') }
    let(:learner) { create(:learner) }

    it 'marks as correct when answer matches' do
      response = create(:quiz_response,
        lesson: lesson,
        learner: learner,
        user_answer: 'correct_answer',
        is_correct: true
      )
      expect(response.is_correct).to be true
    end

    it 'marks as incorrect when answer does not match' do
      response = create(:quiz_response,
        lesson: lesson,
        learner: learner,
        user_answer: 'wrong_answer',
        is_correct: false
      )
      expect(response.is_correct).to be false
    end
  end

  describe 'time tracking' do
    let(:response) { create(:quiz_response) }

    it 'records time spent' do
      expect(response.time_spent_seconds).to be_present
      expect(response.time_spent_seconds).to be > 0
    end

    it 'tracks multiple attempts' do
      response_with_retries = create(:quiz_response, :multiple_attempts)
      expect(response_with_retries.attempts).to be > 1
    end
  end

  describe 'validation edge cases' do
    let(:lesson) { create(:lesson) }
    let(:learner) { create(:learner) }

    it 'requires answer_given' do
      response = build(:quiz_response, answer_given: nil)
      expect(response).not_to be_valid
      expect(response.errors[:answer_given]).to include("can't be blank")
    end

    it 'requires correct to be boolean' do
      response = build(:quiz_response, correct: nil)
      expect(response).not_to be_valid
    end

    it 'allows true for correct' do
      response = build(:quiz_response, correct: true)
      expect(response).to be_valid
    end

    it 'allows false for correct' do
      response = build(:quiz_response, correct: false)
      expect(response).to be_valid
    end
  end

  describe 'learner association' do
    let(:learner) { create(:learner) }
    let(:lesson) { create(:lesson) }

    it 'belongs to a learner' do
      response = create(:quiz_response, learner: learner, lesson: lesson)
      expect(response.learner).to eq(learner)
    end

    it 'requires a learner' do
      response = build(:quiz_response, learner: nil)
      expect(response).not_to be_valid
    end
  end

  describe 'lesson association' do
    let(:lesson) { create(:lesson) }

    it 'belongs to a lesson' do
      response = create(:quiz_response, lesson: lesson)
      expect(response.lesson).to eq(lesson)
    end

    it 'requires a lesson' do
      response = build(:quiz_response, lesson: nil)
      expect(response).not_to be_valid
    end
  end
end
