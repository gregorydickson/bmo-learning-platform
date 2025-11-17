# frozen_string_literal: true

require 'rails_helper'

RSpec.describe LearningPath, type: :model do
  describe 'associations' do
    it { should belong_to(:learner) }
    it { should have_many(:lessons).dependent(:destroy) }
  end

  describe 'validations' do
    it { should validate_presence_of(:topic) }
    it { should validate_inclusion_of(:status).in_array(%w[active paused completed]) }
  end

  describe 'factory' do
    it 'has a valid factory' do
      expect(build(:learning_path)).to be_valid
    end

    it 'creates completed learning path' do
      path = create(:learning_path, :completed)
      expect(path.status).to eq('completed')
      expect(path.progress).to eq(100.0)
      expect(path.completed_at).to be_present
    end

    it 'creates in_progress learning path' do
      path = create(:learning_path, :in_progress)
      expect(path.status).to eq('in_progress')
      expect(path.progress).to eq(45.0)
    end
  end

  describe 'scopes' do
    let!(:active_path) { create(:learning_path, status: 'active') }
    let!(:completed_path) { create(:learning_path, status: 'completed') }
    let!(:paused_path) { create(:learning_path, status: 'paused') }

    describe '.active' do
      it 'returns only active learning paths' do
        expect(LearningPath.active).to include(active_path)
        expect(LearningPath.active).not_to include(completed_path)
        expect(LearningPath.active).not_to include(paused_path)
      end
    end

    describe '.completed' do
      it 'returns only completed learning paths' do
        expect(LearningPath.completed).to include(completed_path)
        expect(LearningPath.completed).not_to include(active_path)
        expect(LearningPath.completed).not_to include(paused_path)
      end
    end
  end

  describe '#progress_percentage' do
    context 'with no lessons' do
      let(:path) { create(:learning_path, total_lessons: 0, lessons_completed: 0) }

      it 'returns 0' do
        expect(path.progress_percentage).to eq(0)
      end
    end

    context 'with lessons in progress' do
      let(:path) { create(:learning_path, total_lessons: 10, lessons_completed: 3) }

      it 'calculates correct percentage' do
        expect(path.progress_percentage).to eq(30.0)
      end
    end

    context 'with half completed' do
      let(:path) { create(:learning_path, total_lessons: 20, lessons_completed: 10) }

      it 'returns 50%' do
        expect(path.progress_percentage).to eq(50.0)
      end
    end

    context 'with all completed' do
      let(:path) { create(:learning_path, total_lessons: 5, lessons_completed: 5) }

      it 'returns 100%' do
        expect(path.progress_percentage).to eq(100.0)
      end
    end

    context 'with fractional completion' do
      let(:path) { create(:learning_path, total_lessons: 3, lessons_completed: 1) }

      it 'rounds to 2 decimal places' do
        expect(path.progress_percentage).to eq(33.33)
      end
    end
  end

  describe '#complete!' do
    let(:path) { create(:learning_path, status: 'active') }

    it 'sets status to completed' do
      path.complete!
      expect(path.status).to eq('completed')
    end

    it 'persists the change' do
      path.complete!
      path.reload
      expect(path.status).to eq('completed')
    end

    it 'can complete paused path' do
      path.update!(status: 'paused')
      path.complete!
      expect(path.reload.status).to eq('completed')
    end
  end

  describe 'status validation' do
    let(:path) { build(:learning_path) }

    it 'accepts valid statuses' do
      %w[active paused completed].each do |status|
        path.status = status
        expect(path).to be_valid
      end
    end

    it 'rejects invalid statuses' do
      path.status = 'invalid_status'
      expect(path).not_to be_valid
      expect(path.errors[:status]).to be_present
    end
  end

  describe 'destruction' do
    let!(:path) { create(:learning_path) }
    let!(:lesson) { create(:lesson, learning_path: path) }

    it 'destroys associated lessons' do
      expect { path.destroy }.to change { Lesson.count }.by(-1)
    end
  end

  describe 'default values' do
    let(:path) { create(:learning_path) }

    it 'defaults status to active' do
      expect(path.status).to eq('active')
    end

    it 'defaults progress to 0' do
      expect(path.progress).to eq(0.0)
    end
  end
end
