"""

CLAMS app to detect scenes with text.

The kinds of scenes that are recognized include slates, chryons and credits.

"""

import argparse
import logging
from typing import Union

from clams import ClamsApp, Restifier
from mmif import Mmif, View, Annotation, Document, AnnotationTypes, DocumentTypes

import classify


logging.basicConfig(filename='swt.log', level=logging.DEBUG)


class SwtDetection(ClamsApp):

    def __init__(self, configs):
        super().__init__()
        self.classifier = classify.Classifier(configs)


    def _appmetadata(self):
        # see https://sdk.clams.ai/autodoc/clams.app.html#clams.app.ClamsApp._load_appmetadata
        # Also check out ``metadata.py`` in this directory. 
        # When using the ``metadata.py`` leave this do-nothing "pass" method here. 
        pass

    def _annotate(self, mmif: Union[str, dict, Mmif], **parameters) -> Mmif:
        # see https://sdk.clams.ai/autodoc/clams.app.html#clams.app.ClamsApp._annotate

        vds = mmif.get_documents_by_type(DocumentTypes.VideoDocument)
        if not vds:
            # TODO: should add warning
            return mmif
        vd = vds[0]

        # calculate the frame predictions and extract the timeframes
        predictions = self.classifier.process_video(vd.location)
        timeframes = self.classifier.extract_timeframes(predictions)

        # aad the timeframes to a new view and return the updated Mmif object
        new_view: View = mmif.new_view()
        self.sign_view(new_view, parameters)
        new_view.new_contain(AnnotationTypes.TimeFrame, document=vd.id)
        for tf in timeframes:
            start, end, score, label = tf
            timeframe_annotation = new_view.new_annotation(AnnotationTypes.TimeFrame)
            timeframe_annotation.add_property("start", start)
            timeframe_annotation.add_property("end", end)
            timeframe_annotation.add_property("frameType", label),
            timeframe_annotation.add_property("score", score)
        return mmif


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="The YAML config file")
    parser.add_argument("--port", action="store", default="5000", help="set port to listen" )
    parser.add_argument("--production", action="store_true", help="run gunicorn server")

    parsed_args = parser.parse_args()
    CONFIGS = parsed_args.configs

    app = SwtDetection(CONFIGS)

    http_app = Restifier(app, port=int(parsed_args.port))
    # for running the application in production mode
    if parsed_args.production:
        http_app.serve_production()
    # development mode
    else:
        app.logger.setLevel(logging.DEBUG)
        http_app.run()
