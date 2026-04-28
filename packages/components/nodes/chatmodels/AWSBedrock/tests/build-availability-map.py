#!/usr/bin/env python3
"""Discover which Bedrock models are available in which regions.

Calls `aws bedrock list-foundation-models` across all Bedrock regions
and saves the results to model-availability.json.

Usage: python3 build-availability-map.py
"""
import json, subprocess, os, sys

# Regions from models.json that are likely to have Bedrock
# (skip cn-* regions which need special auth)
REGIONS = [
    "us-east-1", "us-east-2", "us-west-2",
    "eu-west-1", "eu-west-2", "eu-west-3", "eu-central-1", "eu-central-2",
    "eu-north-1", "eu-south-1", "eu-south-2",
    "ap-southeast-1", "ap-southeast-2", "ap-southeast-3", "ap-southeast-4", "ap-southeast-5",
    "ap-northeast-1", "ap-northeast-2", "ap-northeast-3",
    "ap-south-1", "ap-south-2", "ap-east-1",
    "ca-central-1", "ca-west-1",
    "sa-east-1",
    "me-south-1", "me-central-1",
    "af-south-1",
    "il-central-1",
]

def list_models_in_region(region):
    """Call AWS API to get active text/chat models in a region."""
    try:
        result = subprocess.run(
            ["aws", "bedrock", "list-foundation-models",
             "--region", region,
             "--query", "modelSummaries[?contains(outputModalities, 'TEXT') && modelLifecycle.status == 'ACTIVE'].[modelId]",
             "--output", "json"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return None, result.stderr.strip()[:100]
        data = json.loads(result.stdout)
        # Flatten [[id], [id], ...] to [id, id, ...]
        models = [m[0] for m in data if m]
        # Filter out size variants (e.g., :24k, :300k)
        base_models = []
        for m in models:
            parts = m.split(':')
            if len(parts) <= 2 or parts[-1] in ('0', '1', '2'):
                base_models.append(m)
        return base_models, None
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except Exception as e:
        return None, str(e)[:100]

if __name__ == "__main__":
    # Load our catalog to know which models to track
    models_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'models.json')
    with open(models_path) as f:
        catalog = json.load(f)
    bedrock = next(c for c in catalog['chat'] if c['name'] == 'awsChatBedrock')
    our_models = set(m['name'] for m in bedrock['models'])

    # Build availability map: model_id -> [regions]
    availability = {}
    region_errors = {}

    print(f"Scanning {len(REGIONS)} regions for {len(our_models)} models...\n")

    for region in REGIONS:
        print(f"  {region:<25} ", end="", flush=True)
        models, err = list_models_in_region(region)
        if err:
            print(f"SKIP ({err[:60]})")
            region_errors[region] = err
            continue

        matched = [m for m in models if m in our_models]
        print(f"OK ({len(matched)} models)")

        for m in matched:
            availability.setdefault(m, []).append(region)

    # Save results
    output_path = os.path.join(os.path.dirname(__file__), 'model-availability.json')
    output = {
        "generated": "Run build-availability-map.py to regenerate",
        "regions_scanned": [r for r in REGIONS if r not in region_errors],
        "regions_skipped": region_errors,
        "models": {k: sorted(v) for k, v in sorted(availability.items())}
    }
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
        f.write('\n')

    # Summary
    print(f"\n{'='*60}")
    print(f"Regions scanned: {len(REGIONS) - len(region_errors)}")
    print(f"Regions skipped: {len(region_errors)}")
    print(f"Models found: {len(availability)}")
    total_combos = sum(len(v) for v in availability.values())
    print(f"Total model+region combinations: {total_combos}")
    print(f"\nSaved to: {output_path}")

    # Models in our catalog but not found in any region
    missing = our_models - set(availability.keys())
    if missing:
        print(f"\nModels in catalog but not found in any scanned region:")
        for m in sorted(missing):
            print(f"  {m}")
