# How to Submit
This competition is result-submission only. Please upload BIDS-event files reporting motor unit spike trains for each provided recording.

## Algorithm Submission
This is a prediction submission competition. During both the **Familiarization Phase** and the **Showdown Phase**, you will be asked to upload, for each recording, a tabular file (`recording-<rec_label>_challenge-<challenge_label>_desc-decomposed_events.tsv`) containing your predicted motor unit spikes (BIDS-events file) together with a log file (`recording-<rec_label>_challenge-<challenge_label>_desc-decomposed_log.json`) describing essential process metadata (further details to be announced). Submissions apply to both tasks (**Isometric** and **Dynamic**) independently. To be eligible for awards, you need to share your code openly (e.g., on GitHub) upon the completion of the competition.

## Result File Formats
Here is a minimal example of the format ([BIDS-event file](https://bids-specification.readthedocs.io/en/stable/modality-agnostic-files/events.html)) used for submitting motor unit spike trains

<table style="width: 100%; table-layout: fixed;">
  <thead>
    <tr>
      <th style="width: 20%;">onset</th>
      <th style="width: 20%;">duration</th>
      <th style="width: 20%;">sample</th>
      <th style="width: 20%;">unit_id</th>
      <th style="width: 20%;">description</th>
    </tr>
  </thead>

  <tbody>
    <tr>
      <td>0.001</td>
      <td>0</td>
      <td>1</td>
      <td>0</td>
      <td>motor-unit-spike</td>
    </tr>
    <tr>
      <td>0.005</td>
      <td>0</td>
      <td>5</td>
      <td>1</td>
      <td>motor-unit-spike</td>
    </tr>
    <tr>
      <td>0.011</td>
      <td>0</td>
      <td>11</td>
      <td>0</td>
      <td>motor-unit-spike</td>
    </tr>
    <tr>
      <td>0.012</td>
      <td>0</td>
      <td>12</td>
      <td>2</td>
      <td>motor-unit-spike</td>
    </tr>
    <tr>
      <td>0.016</td>
      <td>0</td>
      <td>16</td>
      <td>1</td>
      <td>motor-unit-spike</td>
    </tr>
    <tr>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>motor-unit-spike</td>
    </tr>
  </tbody>
</table>

- *onset*: Onset (in seconds) of the event, measured from the beginning of the acquisition.
- *duration*: Duration of the event (measured from onset) in seconds. As a motor unit spike can be regarded as a Dirac impulse, its duration is zero.  
- *sample*: Sample index of the event onset (zero-indexing).
- *unit_id*: Unique identifier (integer value) of the motor unit corresponding to the detected spike.
- *description*: Human-readable free-text description of the event.

## Submission Format
codabench platform enforces all submissions to be a .zip archive.<br/>**Important**: Ensure that event-files are located at the root-directory of the zip-Archive
```
exampleSubmission.zip
├── sub-01_exampleRecordingName_events.tsv
├── sub-01_exampleRecordingName_log.json
├── ...
├── sub-0N_exampleRecordingName_events.tsv
└── sub-0N_exampleRecordingName_log.json
```

## Further Information
**More information coming soon!**

Please refer to https://munitquest.github.io/registration_and_submission/ and the provided **starter kit**! (coming soon)
