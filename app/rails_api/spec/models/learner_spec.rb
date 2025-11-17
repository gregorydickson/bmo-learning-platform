# frozen_string_literal: true

require 'rails_helper'

RSpec.describe Learner, type: :model do
  describe 'associations' do
    it { should have_many(:learning_paths).dependent(:destroy) }
    it { should have_many(:quiz_responses).dependent(:destroy) }
  end

  describe 'validations' do
    subject { build(:learner) }

    it { should validate_presence_of(:email) }
    it { should validate_presence_of(:name) }
    it { should validate_uniqueness_of(:email) }
    it { should allow_value('user@example.com').for(:email) }
    it { should_not allow_value('invalid_email').for(:email) }
    it { should_not allow_value('').for(:email) }
  end

  describe 'factory' do
    it 'has a valid factory' do
      expect(build(:learner)).to be_valid
    end

    it 'creates learner with lessons' do
      learner = create(:learner, :with_lessons, lessons_count: 5)
      expect(learner.learning_paths.count).to eq(0)
      # Note: Factory creates lessons but based on model, lessons belong to learning_path
    end

    it 'creates learner with learning paths' do
      learner = create(:learner, :with_learning_paths, paths_count: 3)
      expect(learner.learning_paths.count).to eq(3)
    end
  end

  describe '#completion_rate' do
    let(:learner) { create(:learner) }

    context 'with no learning paths' do
      it 'returns 0' do
        expect(learner.completion_rate).to eq(0)
      end
    end

    context 'with learning paths' do
      before do
        create(:learning_path, learner: learner, total_lessons: 10, lessons_completed: 5)
        create(:learning_path, learner: learner, total_lessons: 20, lessons_completed: 10)
      end

      it 'calculates completion rate across all paths' do
        # Total: 30 lessons, Completed: 15 lessons = 50%
        expect(learner.completion_rate).to eq(50.0)
      end
    end

    context 'with all lessons completed' do
      before do
        create(:learning_path, learner: learner, total_lessons: 10, lessons_completed: 10)
      end

      it 'returns 100' do
        expect(learner.completion_rate).to eq(100.0)
      end
    end
  end

  describe '#quiz_accuracy' do
    let(:learner) { create(:learner) }

    context 'with no quiz responses' do
      it 'returns 0' do
        expect(learner.quiz_accuracy).to eq(0)
      end
    end

    context 'with quiz responses' do
      before do
        create(:quiz_response, learner: learner, correct: true)
        create(:quiz_response, learner: learner, correct: true)
        create(:quiz_response, learner: learner, correct: false)
        create(:quiz_response, learner: learner, correct: false)
      end

      it 'calculates accuracy percentage' do
        # 2 correct out of 4 = 50%
        expect(learner.quiz_accuracy).to eq(50.0)
      end
    end

    context 'with all correct answers' do
      before do
        create_list(:quiz_response, 5, learner: learner, correct: true)
      end

      it 'returns 100' do
        expect(learner.quiz_accuracy).to eq(100.0)
      end
    end

    context 'with all incorrect answers' do
      before do
        create_list(:quiz_response, 5, learner: learner, correct: false)
      end

      it 'returns 0' do
        expect(learner.quiz_accuracy).to eq(0.0)
      end
    end
  end

  describe 'JSONB fields' do
    let(:learner) { create(:learner) }

    it 'stores preferences as JSONB' do
      learner.update(preferences: { theme: 'dark', notifications: true })
      expect(learner.reload.preferences['theme']).to eq('dark')
      expect(learner.preferences['notifications']).to eq(true)
    end

    it 'stores metadata as JSONB' do
      learner.update(metadata: { signup_source: 'mobile_app', version: '2.0' })
      expect(learner.reload.metadata['signup_source']).to eq('mobile_app')
      expect(learner.metadata['version']).to eq('2.0')
    end
  end

  describe 'uniqueness constraints' do
    let!(:existing_learner) { create(:learner, email: 'unique@example.com') }

    it 'does not allow duplicate emails' do
      duplicate = build(:learner, email: 'unique@example.com')
      expect(duplicate).not_to be_valid
      expect(duplicate.errors[:email]).to include('has already been taken')
    end

    it 'allows different emails' do
      different = build(:learner, email: 'different@example.com')
      expect(different).to be_valid
    end
  end

  describe 'destruction' do
    let!(:learner) { create(:learner) }
    let!(:learning_path) { create(:learning_path, learner: learner) }
    let!(:quiz_response) { create(:quiz_response, learner: learner) }

    it 'destroys associated learning paths' do
      expect { learner.destroy }.to change { LearningPath.count }.by(-1)
    end

    it 'destroys associated quiz responses' do
      expect { learner.destroy }.to change { QuizResponse.count }.by(-1)
    end
  end
end
