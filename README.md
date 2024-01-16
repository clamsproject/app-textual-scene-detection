# Scenes-with-text 


## Description

Proof of concept prototype for an app that extracts scenes with textual content. The default model included in the app extracts slates, chyrons and credits.


## User instructions

General user instructions for CLAMS apps are available at the [CLAMS Apps documentation](https://apps.clams.ai/clamsapp).


### System requirements

The preferred platform is Debian 10.13 or higher, but the code is known to run on MacOSX. GPU is not required but performance will be better with it. The main system packages needed are FFmpeg ([https://ffmpeg.org/](https://ffmpeg.org/)), OpenCV4 ([https://opencv.org/](https://opencv.org/)), and Python 3.8 or higher. 

The easiest way to get these is to get the Docker [clams-python-opencv4](https://github.com/clamsproject/clams-python/pkgs/container/clams-python-opencv4) base image. For more details take a peek at the following container specifications for the CLAMS [base]((https://github.com/clamsproject/clams-python/blob/main/container/Containerfile)),  [FFMpeg](https://github.com/clamsproject/clams-python/blob/main/container/ffmpeg.containerfile) and [OpenCV](https://github.com/clamsproject/clams-python/blob/main/container/ffmpeg.containerfile) containers. Python packages needed are: clams-python, ffmpeg-python, opencv-python-rolling, torch, torchmetrics, torchvision, av, pyyaml and tqdm. Some of these are installed on the Docker [clams-python-opencv4](https://github.com/clamsproject/clams-python/pkgs/container/clams-python-opencv4) base image and some are listed in `requirements-app.txt` in this repository.


### Configurable runtime parameters

Apps can be configured at request time using [URL query strings](https://en.wikipedia.org/wiki/Query_string). For runtime parameter supported by this app, please visit the [CLAMS App Directory](https://apps.clams.ai) and look for the app name and version. 


### Running the application

To build the Docker image and run the container

```bash
docker build -t app-swt -f Containerfile .
docker run --rm -d -v /Users/Shared/archive/:/data -p 5000:5000 app-swt
```

The path `/Users/Shared/archive/` should be edited to match your local configuaration.

Using the app to process a MMIF file:

```bash
curl -X POST -d@example-mmif.json http://localhost:5000/
```

This may take a while depending on the size of the video file embedded in the MMIF file. It should return a MMIF object with timeframes added, for example

```json
{
  "metadata": {
    "mmif": "http://mmif.clams.ai/0.4.0"
  },
  "documents": [
    {
      "@type": "http://mmif.clams.ai/0.4.0/vocabulary/VideoDocument",
      "properties": {
        "mime": "video/mpeg",
        "id": "m1",
        "location": "file:///data/video/cpb-aacip-690722078b2-shrunk.mp4"
      }
    }
  ],
  "views": [
    {
      "id": "v_0",
      "metadata": {
        "timestamp": "2023-11-06T20:00:18.311889",
        "app": "http://apps.clams.ai/swt-detection",
        "contains": {
          "http://mmif.clams.ai/vocabulary/TimeFrame/v1": {
            "document": "m1"
          }
        },
        "parameters": {
          "pretty": "True"
        }
      },
      "annotations": [
        {
          "@type": "http://mmif.clams.ai/vocabulary/TimeFrame/v1",
          "properties": {
            "start": 30000,
            "end": 40000,
            "frameType": "slate",
            "score": 3.909090909090909,
            "id": "tf_1"
          }
        },
        {
          "@type": "http://mmif.clams.ai/vocabulary/TimeFrame/v1",
          "properties": {
            "start": 56000,
            "end": 58000,
            "frameType": "slate",
            "score": 1.3333333333333333,
            "id": "tf_2"
          }
        }
      ]
    }
  ]
}
```
