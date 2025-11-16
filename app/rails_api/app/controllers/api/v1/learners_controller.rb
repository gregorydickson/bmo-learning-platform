# frozen_string_literal: true

module Api
  module V1
    class LearnersController < ApplicationController
      before_action :set_learner, only: [:show, :update, :progress]

      def index
        learners = Learner.all
        render json: learners
      end

      def show
        render json: @learner
      end

      def create
        learner = Learner.new(learner_params)

        if learner.save
          render json: learner, status: :created
        else
          render json: { errors: learner.errors }, status: :unprocessable_entity
        end
      end

      def update
        if @learner.update(learner_params)
          render json: @learner
        else
          render json: { errors: @learner.errors }, status: :unprocessable_entity
        end
      end

      def progress
        render json: {
          learner_id: @learner.id,
          completion_rate: @learner.completion_rate,
          quiz_accuracy: @learner.quiz_accuracy,
          learning_paths: @learner.learning_paths.map do |path|
            {
              id: path.id,
              topic: path.topic,
              status: path.status,
              progress: path.progress_percentage
            }
          end
        }
      end

      private

      def set_learner
        @learner = Learner.find(params[:id])
      end

      def learner_params
        params.require(:learner).permit(:email, :name, :phone, :slack_user_id, :preferences, :metadata)
      end
    end
  end
end
