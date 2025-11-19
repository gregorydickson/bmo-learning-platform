# frozen_string_literal: true

require 'rails_helper'

RSpec.describe Document, type: :model do
  describe 'validations' do
    subject do
      described_class.new(
        filename: 'test.pdf',
        s3_bucket: 'bmo-learning-test-documents',
        s3_key: 'uploads/test.pdf',
        category: 'lesson'
      )
    end

    it { is_expected.to validate_presence_of(:filename) }
    it { is_expected.to validate_presence_of(:s3_bucket) }
    it { is_expected.to validate_presence_of(:s3_key) }
    it { is_expected.to validate_inclusion_of(:category).in_array(%w[lesson reference quiz general]) }
    it { is_expected.to validate_uniqueness_of(:s3_key) }
  end

  describe 'associations' do
    it { is_expected.to belong_to(:learner).optional }
    it { is_expected.to belong_to(:uploader).class_name('User').with_foreign_key('uploaded_by').optional }
  end

  describe 'scopes' do
    let!(:processed_doc) do
      described_class.create!(
        filename: 'processed.pdf',
        s3_bucket: 'test-bucket',
        s3_key: 'uploads/processed.pdf',
        processed: true,
        processed_at: 1.hour.ago
      )
    end

    let!(:pending_doc) do
      described_class.create!(
        filename: 'pending.pdf',
        s3_bucket: 'test-bucket',
        s3_key: 'uploads/pending.pdf',
        processed: false
      )
    end

    let!(:lesson_doc) do
      described_class.create!(
        filename: 'lesson.pdf',
        s3_bucket: 'test-bucket',
        s3_key: 'uploads/lesson.pdf',
        category: 'lesson'
      )
    end

    let!(:reference_doc) do
      described_class.create!(
        filename: 'reference.pdf',
        s3_bucket: 'test-bucket',
        s3_key: 'uploads/reference.pdf',
        category: 'reference'
      )
    end

    describe '.processed' do
      it 'returns only processed documents' do
        expect(described_class.processed).to contain_exactly(processed_doc)
      end
    end

    describe '.pending' do
      it 'returns only pending documents' do
        expect(described_class.pending).to include(pending_doc, lesson_doc, reference_doc)
        expect(described_class.pending).not_to include(processed_doc)
      end
    end

    describe '.by_category' do
      it 'returns documents of specified category' do
        expect(described_class.by_category('lesson')).to contain_exactly(lesson_doc)
        expect(described_class.by_category('reference')).to contain_exactly(reference_doc)
      end
    end

    describe '.by_learner' do
      let!(:learner_doc) do
        described_class.create!(
          filename: 'learner.pdf',
          s3_bucket: 'test-bucket',
          s3_key: 'uploads/learner.pdf',
          learner_id: 123
        )
      end

      it 'returns documents for specified learner' do
        expect(described_class.by_learner(123)).to contain_exactly(learner_doc)
      end
    end

    describe '.recent' do
      it 'returns documents ordered by created_at desc' do
        # Reference doc is created last, so it should be first
        expect(described_class.recent.first).to eq(reference_doc)
      end
    end
  end

  describe '#processed?' do
    it 'returns true when processed is true' do
      document = described_class.new(processed: true)
      expect(document.processed?).to be true
    end

    it 'returns false when processed is false' do
      document = described_class.new(processed: false)
      expect(document.processed?).to be false
    end
  end

  describe '#mark_processed!' do
    let(:document) do
      described_class.create!(
        filename: 'test.pdf',
        s3_bucket: 'test-bucket',
        s3_key: 'uploads/test.pdf',
        processed: false
      )
    end

    it 'marks document as processed' do
      freeze_time do
        document.mark_processed!

        expect(document.processed).to be true
        expect(document.processed_at).to eq(Time.current)
        expect(document.processing_error).to be_nil
      end
    end

    it 'clears any previous processing error' do
      document.update!(processing_error: 'Previous error')

      document.mark_processed!

      expect(document.processing_error).to be_nil
    end
  end

  describe '#mark_failed!' do
    let(:document) do
      described_class.create!(
        filename: 'test.pdf',
        s3_bucket: 'test-bucket',
        s3_key: 'uploads/test.pdf',
        processed: false
      )
    end

    it 'marks document as failed with error message' do
      freeze_time do
        document.mark_failed!('Processing error: Invalid PDF')

        expect(document.processed).to be false
        expect(document.processed_at).to eq(Time.current)
        expect(document.processing_error).to eq('Processing error: Invalid PDF')
      end
    end
  end

  describe '#s3_uri' do
    let(:document) do
      described_class.new(
        s3_bucket: 'my-bucket',
        s3_key: 'uploads/2025/document.pdf'
      )
    end

    it 'returns S3 URI format' do
      expect(document.s3_uri).to eq('s3://my-bucket/uploads/2025/document.pdf')
    end
  end

  describe '#human_size' do
    it 'returns formatted size for bytes' do
      document = described_class.new(size: 500)
      expect(document.human_size).to eq('500.00 B')
    end

    it 'returns formatted size for kilobytes' do
      document = described_class.new(size: 1024)
      expect(document.human_size).to eq('1.00 KB')
    end

    it 'returns formatted size for megabytes' do
      document = described_class.new(size: 1_048_576)
      expect(document.human_size).to eq('1.00 MB')
    end

    it 'returns formatted size for gigabytes' do
      document = described_class.new(size: 1_073_741_824)
      expect(document.human_size).to eq('1.00 GB')
    end

    it 'returns Unknown when size is nil' do
      document = described_class.new(size: nil)
      expect(document.human_size).to eq('Unknown')
    end

    it 'handles fractional sizes' do
      document = described_class.new(size: 1536) # 1.5 KB
      expect(document.human_size).to eq('1.50 KB')
    end
  end
end
