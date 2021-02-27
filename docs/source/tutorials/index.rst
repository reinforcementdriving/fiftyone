.. _tutorials:

FiftyOne Tutorials
==================

.. default-role:: code

Welcome to FiftyOne tutorials!

Each tutorial below is a curated demonstration of how FiftyOne can help refine
your datasets and turn your good models into *great models*.

.. Tutorial cards section -----------------------------------------------------

.. raw:: html

    <div id="tutorial-cards-container">

    <nav class="navbar navbar-expand-lg navbar-light tutorials-nav col-12">
        <div class="tutorial-tags-container">
            <div id="dropdown-filter-tags">
                <div class="tutorial-filter-menu">
                    <div class="tutorial-filter filter-btn all-tag-selected" data-tag="all">All</div>
                </div>
            </div>
        </div>
    </nav>

    <hr class="tutorials-hr">

    <div class="row">

    <div id="tutorial-cards">
    <div class="list">

.. Add tutorial cards below

.. customcarditem::
    :header: Evaluating object detections
    :description: Aggregate statistics aren't sufficient for object detection. This tutorial shows how to use FiftyOne to perform powerful evaluation workflows on your detector.
    :link: evaluate_detections.html
    :image: ../_static/images/tutorials/evaluate_detections.png
    :tags: Getting-Started,Model-Evaluation

.. customcarditem::
    :header: Evaluating a classifier
    :description: Evaluation made easy. This tutorial walks through and end-to-end example of fine-tuning a classifier and understanding its failure modes using FiftyOne.
    :link: evaluate_classifications.html
    :image: ../_static/images/tutorials/evaluate_classifications.png
    :tags: Getting-Started,Model-Evaluation

.. customcarditem::
    :header: Exploring image uniqueness
    :description: Your models need diverse data. This tutorial shows how FiftyOne can remove near-duplicate images and recommend unique samples for model training.
    :link: uniqueness.html
    :image: ../_static/images/tutorials/uniqueness.png
    :tags: Getting-Started,Dataset-Evaluation,Brian

.. customcarditem::
    :header: Finding classification mistakes
    :description: Better models start with better data. This tutorial shows how FiftyOne can automatically find possible label mistakes in your classification datasets.
    :link: classification_mistakes.html
    :image: ../_static/images/tutorials/classification_mistakes.png
    :tags: Getting-Started,Dataset-Evaluation,Brian

.. customcarditem::
    :header: Finding detection mistakes
    :description: How good are your ground truth objects? Use the FiftyOne Brain's mistakenness feature to find annotation errors in your object detections.
    :link: detection_mistakes.html
    :image: ../_static/images/tutorials/detection_mistakes.png
    :tags: Getting-Started,Dataset-Evaluation,Brian

.. End of tutorial cards

.. raw:: html

    </div>

    <div class="pagination d-flex justify-content-center"></div>

    </div>

    </div>

.. End tutorial cards section -------------------------------------------------

.. note::

    Check out the
    `fiftyone-examples <https://github.com/voxel51/fiftyone-examples>`_
    repository for more examples of using FiftyOne!

.. toctree::
   :maxdepth: 1
   :hidden:

   Evaluating object detections<evaluate_detections.ipynb>
   Evaluating a classifier<evaluate_classifications.ipynb>
   Exploring image uniqueness<uniqueness.ipynb>
   Finding class mistakes<classification_mistakes.ipynb>
   Finding detection mistakes<detection_mistakes.ipynb>
