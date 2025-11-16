# frozen_string_literal: true

module Api
  module V1
    class LearningPathsController < ApplicationController
      def create
        learner = Learner.find(params[:learner_id])
        learning_path = learner.learning_paths.new(learning_path_params)

        if learning_path.save
          # Queue first lesson delivery
          LessonDeliveryJob.perform_later(learning_path.id)

          render json: learning_path, status: :created
        else
          render json: { errors: learning_path.errors }, status: :unprocessable_entity
        end
      end

      private

      def learning_path_params
        params.require(:learning_path).permit(:topic, :total_lessons)
      end
    end
  end
end
