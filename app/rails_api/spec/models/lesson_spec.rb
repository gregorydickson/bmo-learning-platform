# frozen_string_literal: true

require 'rails_helper'

RSpec.describe Lesson, type: :model do
  describe 'associations' do
    it { should belong_to(:learning_path) }
    it { should have_many(:quiz_responses).dependent(:destroy) }
  end

  describe 'validations' do
    it { should validate_presence_of(:topic) }
    it { should validate_presence_of(:content) }
  end

  describe 'factory' do
    it 'has a valid factory' do
      expect(build(:lesson)).to be_valid
    end

    it 'creates completed lesson' do
      lesson = create(:lesson, :completed)
      expect(lesson.status).to eq('completed')
      expect(lesson.completed_at).to be_present
    end

    it 'creates in_progress lesson' do
      lesson = create(:lesson, :in_progress)
      expect(lesson.status).to eq('in_progress')
      expect(lesson.started_at).to be_present
    end
  end

  describe 'scopes' do
    let!(:delivered_lesson) { create(:lesson, delivered_at: 1.hour.ago) }
    let!(:undelivered_lesson) { create(:lesson, delivered_at: nil) }

    describe '.delivered' do
      it 'returns only delivered lessons' do
        expect(Lesson.delivered).to include(delivered_lesson)
        expect(Lesson.delivered).not_to include(undelivered_lesson)
      end
    end

    describe '.undelivered' do
      it 'returns only undelivered lessons' do
        expect(Lesson.undelivered).to include(undelivered_lesson)
        expect(Lesson.undelivered).not_to include(delivered_lesson)
      end
    end
  end

  describe '#delivered?' do
    context 'when delivered_at is present' do
      let(:lesson) { create(:lesson, delivered_at: 1.hour.ago) }

      it 'returns true' do
        expect(lesson.delivered?).to be true
      end
    end

    context 'when delivered_at is nil' do
      let(:lesson) { create(:lesson, delivered_at: nil) }

      it 'returns false' do
        expect(lesson.delivered?).to be false
      end
    end
  end

  describe '#mark_delivered!' do
    let(:lesson) { create(:lesson, delivered_at: nil, delivery_channel: nil) }

    it 'sets delivered_at to current time' do
      freeze_time do
        lesson.mark_delivered!(channel: 'email')
        expect(lesson.delivered_at).to be_within(1.second).of(Time.current)
      end
    end

    it 'sets delivery_channel' do
      lesson.mark_delivered!(channel: 'slack')
      expect(lesson.delivery_channel).to eq('slack')
    end

    it 'persists changes to database' do
      lesson.mark_delivered!(channel: 'sms')
      lesson.reload
      expect(lesson.delivered_at).to be_present
      expect(lesson.delivery_channel).to eq('sms')
    end

    it 'raises error if channel is not provided' do
      expect { lesson.mark_delivered! }.to raise_error(ArgumentError)
    end
  end

  describe 'destruction' do
    let!(:lesson) { create(:lesson) }
    let!(:quiz_response) { create(:quiz_response, lesson: lesson) }

    it 'destroys associated quiz responses' do
      expect { lesson.destroy }.to change { QuizResponse.count }.by(-1)
    end
  end

  describe 'difficulty levels' do
    it 'creates easy lesson' do
      lesson = create(:lesson, :easy)
      expect(lesson.difficulty).to eq('easy')
    end

    it 'creates hard lesson' do
      lesson = create(:lesson, :hard)
      expect(lesson.difficulty).to eq('hard')
    end

    it 'defaults to medium difficulty' do
      lesson = create(:lesson)
      expect(lesson.difficulty).to eq('medium')
    end
  end

  describe 'quiz data' do
    let(:lesson) { create(:lesson) }

    it 'has quiz question' do
      expect(lesson.quiz_question).to be_present
      expect(lesson.quiz_question).to end_with('?')
    end

    it 'has quiz options array' do
      expect(lesson.quiz_options).to be_an(Array)
      expect(lesson.quiz_options.length).to be >= 2
    end

    it 'has quiz answer from options' do
      expect(lesson.quiz_answer).to be_present
      expect(lesson.quiz_options).to include(lesson.quiz_answer)
    end
  end
end
