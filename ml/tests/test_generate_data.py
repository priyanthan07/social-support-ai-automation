"""Synthetic data generation tests."""

from ssa_ml.generate_data import generate


def test_generate_dataset_shape():
    df = generate(n=200, seed=99)
    assert len(df) == 200
    assert "eligible" in df.columns
    assert "support_amount" in df.columns
    assert 0.2 < df["eligible"].mean() < 0.9
