# How to Submit
This competition is result-submission only. Please upload a BIDS-event file reporting motor unit spike trains.

## Result File Formats
Your identified spike trains must be submitted in the form of a BIDS-event tabular file (`exampleRecordingName.tsv`). The following is minimal example:

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
tbd.

For more information and a mock submission, please refer to the provided **starter kit**!