"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const pool = require("../../industry_analysis/static/owner_acceptance_pool.js");

const DIRECT_V1 = "00000000-0000-0000-0000-000000000001";
const DIRECT_V2 = "00000000-0000-0000-0000-000000000002";
const SECONDARY_V1 = "00000000-0000-0000-0000-000000000003";

function contract() {
  return {
    create_contract: {
      pool_key: "new-pool",
      title_default: "新建默认标题",
      scope_default: "新建默认范围",
    },
    append_options: [
      {
        candidate_pool_id: "10000000-0000-0000-0000-000000000001",
        expected_latest_revision_id: "20000000-0000-0000-0000-000000000001",
        revision_number: 4,
        title: "现有候选池标题",
        scope: "现有候选池范围",
      },
    ],
    reuse_options: [
      {
        candidate_pool_id: "10000000-0000-0000-0000-000000000001",
        candidate_pool_revision_id: "20000000-0000-0000-0000-000000000001",
        revision_number: 4,
        title: "精确候选池",
        scope: "精确冻结范围",
        beneficiary_revision_ids: [SECONDARY_V1, DIRECT_V1],
      },
      {
        candidate_pool_id: "10000000-0000-0000-0000-000000000002",
        candidate_pool_revision_id: "20000000-0000-0000-0000-000000000002",
        revision_number: 1,
        title: "部分成员候选池",
        scope: "缺少一个成员",
        beneficiary_revision_ids: [DIRECT_V1],
      },
    ],
  };
}

test("exact set equality is order independent and rejects partial or supersets", () => {
  assert.equal(
    pool.exactIdSetEqual([DIRECT_V1, SECONDARY_V1], [SECONDARY_V1, DIRECT_V1]),
    true,
  );
  assert.equal(pool.exactIdSetEqual([DIRECT_V1], [DIRECT_V1, SECONDARY_V1]), false);
  assert.equal(
    pool.exactIdSetEqual(
      [DIRECT_V1, SECONDARY_V1, DIRECT_V2],
      [DIRECT_V1, SECONDARY_V1],
    ),
    false,
  );
});

test("exact supported revisions require reuse operations for every supported member", () => {
  assert.deepEqual(
    pool.exactSupportedRevisionIds([
      {
        stage1_operation: "reuse_exact_beneficiary_revision",
        assessment_status: "supported",
        beneficiary_revision_id: SECONDARY_V1,
      },
      {
        stage1_operation: "reuse_exact_beneficiary_revision",
        assessment_status: "supported",
        beneficiary_revision_id: DIRECT_V1,
      },
      {
        stage1_operation: "reuse_exact_beneficiary_revision",
        assessment_status: "draft",
        beneficiary_revision_id: DIRECT_V2,
      },
    ]),
    [DIRECT_V1, SECONDARY_V1],
  );
  assert.equal(
    pool.exactSupportedRevisionIds([
      {
        stage1_operation: "append_beneficiary_revision",
        assessment_status: "supported",
        beneficiary_revision_id: null,
      },
    ]),
    null,
  );
});

test("reuse options are exposed only for exact frozen membership", () => {
  const matches = pool.eligibleReuseOptions(
    contract().reuse_options,
    [DIRECT_V1, SECONDARY_V1],
  );
  assert.equal(matches.length, 1);
  assert.equal(
    matches[0].candidate_pool_revision_id,
    "20000000-0000-0000-0000-000000000001",
  );
  assert.deepEqual(pool.eligibleReuseOptions(contract().reuse_options, null), []);
  assert.deepEqual(
    pool.eligibleReuseOptions(contract().reuse_options, [DIRECT_V2, SECONDARY_V1]),
    [],
  );
});

test("append selection uses the selected pool metadata instead of create defaults", () => {
  const selection = pool.resolveSelection(
    contract(),
    "append:10000000-0000-0000-0000-000000000001:20000000-0000-0000-0000-000000000001",
  );
  assert.equal(selection.mode, pool.MODE_APPEND);
  assert.equal(selection.title, "现有候选池标题");
  assert.equal(selection.scope, "现有候选池范围");
  assert.notEqual(selection.title, contract().create_contract.title_default);
  assert.notEqual(selection.scope, contract().create_contract.scope_default);
});

test("exact reuse payload contains only exact pool and revision identities", () => {
  const selection = pool.resolveSelection(
    contract(),
    "reuse:10000000-0000-0000-0000-000000000001:20000000-0000-0000-0000-000000000001",
  );
  assert.equal(selection.mode, pool.MODE_REUSE);
  assert.equal(
    selection.candidate_pool_revision_id,
    "20000000-0000-0000-0000-000000000001",
  );
  assert.equal(Object.hasOwn(selection, "title"), false);
  assert.equal(Object.hasOwn(selection, "scope"), false);
});
