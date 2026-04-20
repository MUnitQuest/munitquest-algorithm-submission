# How to Submit
This competition is result-submission only. Please upload a BIDS-event file reporting motor unit spike trains.

## Algorithm Submission
This is a prediction submission competition. During both the **Familiarization Phase** and the **Showdown Phase**, you will be asked to upload, for each recording, a tabular file (`recordingName_events.tsv`) containing your predicted motor unit spikes (BIDS-events file) together with a log file (`recordingName_log.json`) describing essential process metadata (further details to be announced). Submissions apply to both tasks (**Isometric** and **Dynamic**) independently. To be eligible for awards, you need to share your code openly (e.g., on GitHub) upon the completion of the competition.

## Result File Formats
Your identified spike trains must be submitted in the form of a BIDS-event tabular file (`recordingName_events.tsv`). The following is an example on how to report motor unit spike trains:

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

<br/>Further, the submitted BIDS-event file is to be accompanied by a log-file (`exampleRecordingName_log.json`) describing essential process metadata (further details to be announced).

## Submission Format
Codabench platform enforces all submissions to be a .zip archive.<br/>**Important**: Make sure that the .zip-Archive does not contain any parent directory.
```
exampleSubmission.zip
├── exampleRecordingName.tsv
└── exampleRecordingName_log.json
```

## Further Information
**More information coming soon!**

Please refer to https://munitquest.github.io/registration_and_submission/ and the provided **starter kit**! (coming soon)