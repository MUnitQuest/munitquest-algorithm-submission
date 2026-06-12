import sys
import os
import time

from algorithm_scoring.score_assembler import MUnitQuestAlgorithmChallengeOrchestrator as Scorer


def main():
    input_path: str = sys.argv[1]
    ground_truth_path: str = sys.argv[2]
    output_path: str = sys.argv[3]

    munitquest_scorer: Scorer = Scorer(
        prediction_path=input_path,
        ground_truth_path=ground_truth_path,
    )

    munitquest_scorer.run()
    print(munitquest_scorer.metrics)
    munitquest_scorer.export(output_path)


if __name__ == "__main__":
    main()
