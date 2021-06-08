import numpy as np
import tensorflow as tf


class NewcastleDetector:
    """
    Based on Tom Komar's repository (part of Newcastle University's Urban Observatory):
    https://github.com/TomKomar/uo-object_counting
    """

    def __init__(self, serialized_graph, minimum_confidence=0.33):
        self.minimum_confidence = minimum_confidence

        # temporally hard-coded
        self.categoryIdx = {1: {'name': 'bus'}, 2: {'name': 'car'}, 3: {'name': 'cyclist'}, 4: {'name': 'motorcyclist'},
                            5: {'name': 'person'}, 6: {'name': 'truck'}, 7: {'name': 'van'}}

        model = tf.Graph()
        with model.as_default():
            graph_def = tf.compat.v1.GraphDef()

            graph_def.ParseFromString(serialized_graph)
            tf.import_graph_def(graph_def, name="")

            self.sess = tf.compat.v1.Session(graph=model)

            self.imageTensor = model.get_tensor_by_name("image_tensor:0")
            self.boxesTensor = model.get_tensor_by_name("detection_boxes:0")

            self.scoresTensor = model.get_tensor_by_name("detection_scores:0")
            self.classesTensor = model.get_tensor_by_name("detection_classes:0")
            self.numDetections = model.get_tensor_by_name("num_detections:0")

    def detect(self, img_color_rgb):
        img_tensor = np.expand_dims(img_color_rgb, axis=0)

        (boxes_ndims, scores_ndims, labels_ndims, _N) = self.sess.run(
            [self.boxesTensor, self.scoresTensor, self.classesTensor, self.numDetections],
            feed_dict={self.imageTensor: img_tensor})

        boxes = np.squeeze(boxes_ndims)
        scores = np.squeeze(scores_ndims)
        label_ids = np.squeeze(labels_ndims)

        image_height = img_color_rgb.shape[0]
        image_width = img_color_rgb.shape[1]

        scaled_boxes = []
        for box in boxes:
            scaled_boxes.append([
                int(box[0] * image_height), int(box[1] * image_width),
                int(box[2] * image_height), int(box[3] * image_width)
            ])

        labels = [str(self.categoryIdx[label]["name"]) for label in label_ids]
        labelled_scored_boxes_above_threshold = [[label, [box[0], box[1], box[2], box[3], round(float(score), 4)]]
                                                 for box, score, label in zip(scaled_boxes, scores, labels)
                                                 if score > self.minimum_confidence]

        return labelled_scored_boxes_above_threshold

    def detected_object_types(self):
        return [self.categoryIdx[label_number]["name"] for label_number in self.categoryIdx]

    def close(self):
        self.sess.close()
