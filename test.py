# Lucas Butler
# Testing script

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import time
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, roc_auc_score, confusion_matrix, accuracy_score, ConfusionMatrixDisplay

from utils import read_tfrecords, get_tfrecord_length
from config import GlobalConfiguration
from alexnet import AlexNet
from cnn_small import SmallCNN

model_ = SmallCNN


tf.random.set_seed(1)

# Class for Tester
class Tester(object):

	def __init__(self, cfg, net, testset):
		self.cfg = cfg
		self.net = net
		self.testset = testset

	def test(self):
		'''
		Test the model.
		'''
		all_predictions = []
		all_labels = []

		# Iterate through the test dataset
		start = time.time()
		for samples, labels in self.testset:

			predictions = self.net(samples, training=False)  # Apply sigmoid if needed
			all_predictions.append(predictions.numpy().flatten())  # Collect probabilities

			all_labels.append(labels.numpy().flatten())  # Collect true labels

		end = time.time()
		tf.print(f"\n\nProcessed {len(all_labels) * len(all_labels[0])} samples in {round(end - start, 2)} seconds.")

		# Convert to numpy arrays
		all_predictions = np.concatenate(all_predictions)  # Concatenate batches
		all_labels = np.concatenate(all_labels)  # Concatenate batches

		# Validate data
		assert np.all((all_predictions >= 0) & (all_predictions <= 1))
		assert np.all((all_labels == 0) | (all_labels == 1))

		return all_predictions, all_labels

	def find_best_threshold_and_produce_metrics(self, actual, predicted_probs):
		"""
		Sweeps through thresholds to find the best threshold value based on Youden's Index,
		generates the confusion matrix, and calculates accuracy, precision, recall, and F1 score.

		Inputs:
			actual: np.array - Ground truth binary labels (0 or 1).
			predicted_probs: np.array - Predicted probabilities for the positive class.
		
		Outputs:
			best_threshold: float - The threshold that maximizes Youden's Index.
			accuracy: float - Accuracy at the best threshold.
			precision: float - Precision at the best threshold.
			recall: float - Recall at the best threshold.
			f1: float - F1 score at the best threshold.
		"""
		# Compute ROC curve components
		fpr, tpr, thresholds = roc_curve(actual, predicted_probs)
		auc_score = roc_auc_score(actual, predicted_probs)

		# Plot ROC Curve
		plt.figure(figsize=(7, 7))
		plt.plot(fpr, tpr, label=f'ROC Curve (AUC = {auc_score:.2f})', color='blue')
		plt.plot([0, 1], [0, 1], color='red', linestyle='--', label='Random Chance')
		plt.title('Receiver Operating Characteristic (ROC) Curve')
		plt.xlabel('False Positive Rate')
		plt.ylabel('True Positive Rate')
		plt.legend()
		plt.grid()
		plt.savefig(os.path.join(self.cfg.TESTING_IMAGES, 'ROC_curve.png'))
		
		# Calculate Youden's Index: sensitivity (TPR) - false positive rate (FPR)
		youden_index = tpr + (1 - fpr) - 1
		best_threshold_index = np.argmax(youden_index)  # Index of the best threshold
		best_threshold = thresholds[best_threshold_index]  # Best threshold value
		
		tf.print(f"Best Threshold (Youden's Index): {best_threshold:.4f}")

		# Binarize probabilities using the best threshold
		binary_predictions = (predicted_probs >= best_threshold).astype(int)
		
		# Compute Confusion Matrix
		cm = confusion_matrix(actual, binary_predictions)
		disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=[0, 1])
		disp.plot(cmap=plt.cm.Blues)
		plt.title(f'Confusion Matrix at Best Threshold (Abnormal) {best_threshold:.2f}')
		plt.grid(False)
		plt.savefig(os.path.join(self.cfg.TESTING_IMAGES, 'Confusion_matrix.png'))

		# Calculate Metrics
		accuracy = accuracy_score(actual, binary_predictions)
		# Accuracy of of positive predictions
		precision = np.round(np.sum((binary_predictions == 1) & (actual == 1)) / np.sum(binary_predictions == 1), 2) if np.sum(binary_predictions == 1) > 0 else 0.0
		# ability to idenitify actual positives
		recall = np.round(np.sum((binary_predictions == 1) & (actual == 1)) / np.sum(actual == 1), 2) if np.sum(actual == 1) > 0 else 0.0
		f1 = np.round(2 * (precision * recall) / (precision + recall), 2) if (precision + recall) > 0 else 0.0

		# Print Metrics
		tf.print(f'Accuracy: {accuracy:.2f} | Precision (normal): {precision} | Recall (normal): {recall} | F1 Score (normal): {f1}')
		
		return best_threshold, accuracy, precision, recall, f1
	
if __name__ == '__main__':
	i = 0

	cfg = GlobalConfiguration()

	testset = read_tfrecords(os.path.join(cfg.DATASET_FOLDER, cfg.TEST_FILE), buffer_size=64000)
	testset = testset.batch(128)

	shape = None
	for t in testset.take(1):
		shape = t[0].shape

	# Get the Alexnet form models
	net = model_(cfg=cfg, training=False)
	net.build(input_shape=shape)

	net.load_weights(cfg.MODEL_FILE)

	# Create a tester object
	tester = Tester(cfg, net, testset)

	# Call test function on tester object
	predictions, labels = tester.test()

	# Generate ROC Curve and AUC
	tester.find_best_threshold_and_produce_metrics(labels, predictions)

