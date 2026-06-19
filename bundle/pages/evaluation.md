# Evaluation

## Scoring
For the scoring, we perform the following steps:

- ``(1) Remove duplicate spike trains:`` A duplicate motor unit is detected if two spike trains share at minimum 30 percent of common spikes. In the case of duplicates, we will keep the first unit and reject all other units.
- ``(2) Match predicted and ground truth spike trains:`` Compute for all pairs of predicted and ground truth spike trains the F1-score and match labels by solving a linear sum assignment problem. We require a minimum F1-score of 50 percent.
- ``(3) Label-based score:`` The label-based score of each recording is the sum of all accepted units weighted by their respective F1-score. 

For all isometric recordings with incomplete labels, we additionally perform the following steps for obtaining model-based confidence scores for unmatched sources:

- ``(4) Supervised Fitting of a CBSS Model:`` We use a convolutive blind source separation model (extension factor: 12) and learn the unmixing weights given the predicted spike labels. As there are multiple delayed copies of the same spike train, we will consider all delays within a window of plus/minus 0.1 seconds and use the unmixing weights that yield the highest silhouette-like score. 
- ``(5) Additional metrics:`` To further evaluate the plausibility of the predicted sources, we calculate the pulse-to-noise ratio and the coefficient of dispersion (median absolute deviation divided by the median) of the interspike intervals. 
- ``(6) Bad source rejection:`` All sources with less than 10 spikes or a silhouette-like score below 0.9 are rejected.
- ``(7) Map quality metrics to confidence scores:`` To map the quality metrics (silhouette score, pulse-to-noise-ratio, and the coefficient of dispersion of the interspike intervals) to a normalized confidence score between zero and one, we use a data-driven mapping given in the following table. 
- ``(8) Model-based score:`` To get the model-based score, we compute for each predicted motor unit the mean value of the three metric-based confidence scores and sum these values. 
 
The ``recording score`` is the label-based score plus (if the labels are incomplete) the model-based score. Finally, the ``submission score`` is the average of the ``recording scores`` for the respective task (missing prediction files yield a ``recording score`` of zero).

## Validation
In addition to the calculation of metrics assessing the quality of predictions, each prediction is validated towards the correct submission format. Only valid predictions receive a leaderboard-effective score. Nevertheless, each evaluable prediction is scored to provide some insights regardless of the prediction's validity in terms of submission format.

**Hint**: Validity of the submission-format can be checked pre-submission, using our provided walkthroughs
- [01_familiarisation_isometric.ipynb](https://github.com/MUnitQuest/MUnitQuest_tutorials/blob/main/algorithm_challenge_tutorials/01_familiarisation_isometric.ipynb)
- [02_familiarisation_dynamic.ipynb](https://github.com/MUnitQuest/MUnitQuest_tutorials/blob/main/algorithm_challenge_tutorials/02_familiarisation_dynamic.ipynb)

## Further Information
*for transparency the code of the score function evaluating the submissions is shared: https://github.com/MUnitQuest/munitquest-algorithm-submission*<br/>
<br/>For more information please refer to https://munitquest.github.io/algorithm-challenge/
