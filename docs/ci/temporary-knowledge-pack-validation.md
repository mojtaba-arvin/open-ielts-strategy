# Temporary CI validation branch

This file exists only to open a pull request against the Knowledge Pack feature branch and execute the full CI suite against that branch's current contents. It is not intended to merge into the feature branch or main.

A second validation run is required because the feature base branch gained additional publication-scan and builder changes after the first successful run.

A third validation run includes schema meta-validation and the latest publication leakage scanner changes.

A fourth validation run includes the rolling-hash private-source scanner, local pack builder gate integration, and schema CI checks.

A fifth run validates BM25/dense retrieval integration and the new local embedding CLI option.
