## Simple photo gallery and slideshow


### Description
A flask app that provides state of the art computer vision capabilities combined with a slideshow.

Currently work in progress. Uses Flask backend with SLQAlchemy over Sqlite3. 

### Capabilities
  * Work from local files
  * Detect faces in all photos using MTCNN
  * Create facial embeddings using Arcface (over 20% more accurate on open set accuracy than Dlib on personal data sets)
  * Supports manual labeling of faces
  * Assigns labels for unknown faces using radius neighbors classifier
  
### Todo

  * Create search objects based on people
  * Run slideshow based on search object
  * Add metadata extraction and search
  * Add object recognition and search
  * Add scene recogntiion and search 
  
### Acknolwedgments and citations
Backend is modeled heavily on Miguel Grinberg's Flask Megatutorial: https://github.com/miguelgrinberg/microblog

Front end combines bootstrap, konvas.js and galleria.js

Imports the facenet-pytorch implementation of MTCNN: https://github.com/timesler/facenet-pytorch
Pretrained Arcface model is extracted from https://github.com/foamliu/InsightFace-v2
