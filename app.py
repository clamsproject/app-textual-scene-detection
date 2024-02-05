"""

CLAMS app to detect scenes with text.

The kinds of scenes that are recognized depend on the model used but typically
include slates, chryons and credits.

"""

import argparse
import logging
from pathlib import Path
from typing import Union

import yaml
from clams import ClamsApp, Restifier
from mmif import Mmif, View, AnnotationTypes, DocumentTypes

from modeling import classify, stitch

logging.basicConfig(filename='swt.log', level=logging.DEBUG)

default_config_fname = Path(__file__).parent / 'modeling/config/classifier.yml'


class SwtDetection(ClamsApp):

    def __init__(self, configs):
        super().__init__()
        self.classifier = classify.Classifier(**configs)
        self.stitcher = stitch.Stitcher(**configs)

    def _appmetadata(self):
        # see https://sdk.clams.ai/autodoc/clams.app.html#clams.app.ClamsApp._load_appmetadata
        # Also check out ``metadata.py`` in this directory. 
        # When using the ``metadata.py`` leave this do-nothing "pass" method here. 
        pass

    def _annotate(self, mmif: Union[str, dict, Mmif], **parameters) -> Mmif:

        parameters = self.get_configuration(**parameters)
        new_view: View = mmif.new_view()
        self.sign_view(new_view, parameters)
        self._export_parameters(parameters)

        vds = mmif.get_documents_by_type(DocumentTypes.VideoDocument)
        if not vds:
            warning = Warning('There were no video documents referenced in the MMIF file')
            new_view.metadata.add_warnings(warning)
            return mmif
        vd = vds[0]

        predictions = self.classifier.process_video(vd.location)
        timeframes = self.stitcher.create_timeframes(predictions)

        new_view.new_contain(
            AnnotationTypes.TimeFrame, document=vd.id, timeUnit='milliseconds')
        new_view.new_contain(
            AnnotationTypes.TimePoint, document=vd.id, timeUnit='milliseconds')

        for tf in timeframes:
            timeframe_annotation = new_view.new_annotation(AnnotationTypes.TimeFrame)
            timeframe_annotation.add_property("frameType", tf.label),
            timeframe_annotation.add_property("score", tf.score)
            timeframe_annotation.add_property("scores", tf.scores)
            timepoint_annotations = []
            for prediction in tf.targets:
                timepoint_annotation = new_view.new_annotation(AnnotationTypes.TimePoint)
                prediction.annotation = timepoint_annotation
                timepoint_annotations.append(timepoint_annotation)
                classification = [f"{label}:{prediction.score_for_label(label)}"
                                  for label in prediction.labels]
                label_with_highest_score = self._label_with_highest_score(classification)
                timepoint_annotation.add_property('timePont', prediction.timepoint)
                timepoint_annotation.add_property('label', label_with_highest_score)
                timepoint_annotation.add_property('classification', classification)
            timeframe_annotation.add_property('targets', [tp.id for tp in timepoint_annotations])
            reps = [p.annotation.id for p in tf.representative_predictions()]
            timeframe_annotation.add_property("representatives", reps)
            #print(timeframe_annotation.serialize(pretty=True))

        return mmif

    def _export_parameters(self, parameters: dict):
        """Export the parameters to the Classifier and Stitcher instances."""
        for parameter, value in parameters.items():
            if parameter == "startAt":
                self.classifier.start_at = value
            elif parameter == "stopAt":
                self.classifier.stop_at = value
            elif parameter == "sampleRate":
                self.classifier.sample_rate = value
                self.stitcher.sample_rate = value
            elif parameter == "minFrameScore":
                self.stitcher.min_frame_score = value
            elif parameter == "minTimeframeScore":
                self.stitcher.min_timeframe_score = value
            elif parameter == "minFrameCount":
                self.stitcher.min_frame_count = value

    def _label_with_highest_score(self, classification: list) -> str:
        highest_score = 0
        label_with_highest_score = None
        for classification_pair in classification:
            lbl, score = classification_pair.split(':')
            score = float(score)
            if score > highest_score:
                highest_score = score
                label_with_highest_score = lbl
        return label_with_highest_score
                


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="The YAML config file", default=default_config_fname)
    parser.add_argument("--port", action="store", default="5000", help="set port to listen")
    parser.add_argument("--production", action="store_true", help="run gunicorn server")

    parsed_args = parser.parse_args()
    classifier_configs = yaml.safe_load(open(parsed_args.config))

    app = SwtDetection(classifier_configs)

    http_app = Restifier(app, port=int(parsed_args.port))
    # for running the application in production mode
    if parsed_args.production:
        http_app.serve_production()
    # development mode
    else:
        app.logger.setLevel(logging.DEBUG)
        http_app.run()
