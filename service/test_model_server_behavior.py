"""Tests for the /predict endpoint behaviour."""

import json
import unittest
from unittest.mock import patch

import model_server


class PredictEndpointTests(unittest.TestCase):
    """Covers the model_server.predict Flask view."""

    def setUp(self) -> None:
        self.client = model_server.app.test_client()

    def test_invalid_model_move_flagged_but_not_corrected(self) -> None:
        """The API should surface invalid predictions instead of correcting them."""

        grid = [
            [2, 4, 8, 16],
            [32, 64, 128, 256],
            [512, 1024, 2048, 4096],
            [8192, 16384, 32768, 65536],
        ]

        class FakeModel:
            def predict_proba(self, features):  # type: ignore[override]
                self.last_features = features
                return [[0.05, 0.9, 0.03, 0.02]]

        fake_model = FakeModel()

        with patch("model_server.load_model", return_value=fake_model), patch(
            "model_server.valid_moves", return_value=["UP", "LEFT"]
        ) as mocked_valid_moves:
            response = self.client.post(
                "/predict",
                data=json.dumps({"grid": grid}),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIsNotNone(payload)
        assert payload is not None

        self.assertEqual(payload["move"], "RIGHT")
        self.assertTrue(payload["predicted_invalid"])
        self.assertEqual(payload["valid_moves"], ["UP", "LEFT"])

        self.assertEqual(fake_model.last_features[0].shape, (16,))
        mocked_valid_moves.assert_called_once_with(grid)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
