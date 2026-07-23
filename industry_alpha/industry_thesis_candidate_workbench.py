"""Exact candidate-source reads and deterministic composition for UI Phase 1C."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.canonical_price_models import (
    ListedInstrument,
    ListedInstrumentRevision,
)
from backend.database.models import IngestionRun, StockBasicRecord
from industry_alpha.chain_map_models import IndustryMapRevision
from industry_alpha.industry_thesis_commands import IndustryThesisCommandService
from industry_alpha.industry_thesis_models import (
    IndustryThesisSessionIdentity,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_rules import (
    BUILDER_VERSION,
    IndustryThesisError,
    json_value,
    parse_uuid,
    require_keys,
    stored_utc,
)
from industry_alpha.stage1_models import (
    Stage1Beneficiary,
    Stage1BeneficiaryRevision,
    Stage1CandidatePool,
    Stage1CandidatePoolMembership,
    Stage1CandidatePoolRevision,
)

WORKBENCH_SCOPE_CONTRACT = "aquantai.personal-research-workbench.scope.v1"
_STAGE1_SOURCE_KEYS = {
    "industry_map_revision_id",
    "candidate_pool_revision_id",
    "candidate_pool_membership_id",
    "stage1_beneficiary_revision_id",
}


def _utc_boundary(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            "as_of_recorded_at_utc must be an explicit UTC timestamp",
        )
    return value.astimezone(timezone.utc)


def _visible(
    cutoff: date,
    recorded_at: datetime,
    *,
    as_of_cutoff: date,
    boundary: datetime,
) -> bool:
    return cutoff <= as_of_cutoff and stored_utc(recorded_at) <= boundary


def _exact_one(*values: Any) -> bool:
    return sum(value is not None for value in values) == 1


def _error(code: str, message: str) -> IndustryThesisError:
    return IndustryThesisError(code, message)


class IndustryThesisCandidateWorkbenchService:
    """Read exact candidate sources and compose accepted command payloads only."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def candidate_source_options(
        self,
        *,
        session_id: UUID,
        session_revision_id: UUID,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        boundary = _utc_boundary(as_of_recorded_at_utc)
        identity, revision = self._exact_session_revision(
            session_id=session_id,
            session_revision_id=session_revision_id,
            as_of_cutoff=as_of_cutoff,
            boundary=boundary,
        )
        seeds = self._company_seeds(revision, as_of_cutoff, boundary)
        maps = self._map_source_options(revision, as_of_cutoff, boundary)
        return {
            "session_id": str(identity.id),
            "session_revision_id": str(revision.id),
            "session_revision_number": revision.revision_number,
            "workflow_state": revision.workflow_state,
            "coverage_state": revision.coverage_state,
            "information_cutoff_date": revision.information_cutoff_date.isoformat(),
            "as_of_cutoff": as_of_cutoff.isoformat(),
            "as_of_recorded_at_utc": boundary.isoformat(),
            "is_exact_latest_revision": (
                identity.latest_revision_number == revision.revision_number
            ),
            "build_allowed": (
                identity.latest_revision_number == revision.revision_number
                and revision.workflow_state == "candidate_build_ready"
            ),
            "company_seed_count": len(seeds),
            "company_seeds": seeds,
            "map_count": len(maps),
            "maps": maps,
            "notices": {
                "explicit_pool_selection_required": True,
                "first_pool_not_selected": True,
                "map_title_is_not_company_identity": True,
                "complete_local_universe_not_full_market": True,
                "review_not_enabled": True,
            },
        }

    def compose_candidate_build(
        self,
        *,
        session_id: UUID,
        session_revision_id: UUID,
        expected_session_latest_revision_number: int,
        selected_candidate_pool_revision_ids: Iterable[UUID],
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        options = self.candidate_source_options(
            session_id=session_id,
            session_revision_id=session_revision_id,
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=as_of_recorded_at_utc,
        )
        if not options["is_exact_latest_revision"]:
            raise _error(
                "industry_thesis_revision_conflict",
                "candidate build requires the exact latest session revision",
            )
        if options["workflow_state"] != "candidate_build_ready":
            raise _error(
                "industry_thesis_workflow_invalid",
                "candidate build requires candidate_build_ready workflow state",
            )
        if expected_session_latest_revision_number != options[
            "session_revision_number"
        ]:
            raise _error(
                "industry_thesis_revision_conflict",
                "expected latest session revision does not match",
            )

        selected = list(selected_candidate_pool_revision_ids)
        if len(selected) != len(set(selected)):
            raise _error(
                "industry_thesis_duplicate_source",
                "one candidate build cannot select the same exact pool revision twice",
            )
        eligible: dict[UUID, dict[str, Any]] = {}
        for map_option in options["maps"]:
            for pool in map_option["eligible_candidate_pools"]:
                eligible[UUID(pool["candidate_pool_revision_id"])] = pool
        unknown = sorted(str(value) for value in selected if value not in eligible)
        if unknown:
            raise _error(
                "industry_thesis_source_invalid",
                "selected candidate-pool revision is not an exact eligible source",
            )

        proposals = [
            self._seed_proposal(item, session_revision_id)
            for item in options["company_seeds"]
        ]
        stage1_count = 0
        boundary = _utc_boundary(as_of_recorded_at_utc)
        for pool_revision_id in sorted(selected, key=str):
            pool = eligible[pool_revision_id]
            members = self._pool_members(
                pool_revision_id=pool_revision_id,
                map_revision_id=UUID(pool["industry_map_revision_id"]),
                as_of_cutoff=as_of_cutoff,
                boundary=boundary,
            )
            for member in members:
                proposals.append(self._stage1_proposal(member))
                stage1_count += 1
        if not proposals:
            raise _error(
                "industry_thesis_source_required",
                "candidate build requires at least one exact company seed or frozen Stage 1 member",
            )

        allowed = sorted({proposal["source_kind"] for proposal in proposals})
        command = {
            "session_revision_id": str(session_revision_id),
            "expected_session_latest_revision_number": (
                expected_session_latest_revision_number
            ),
            "builder_version": BUILDER_VERSION,
            "allowed_source_kinds": allowed,
            "proposals": proposals,
        }
        summary = {
            "company_seed_proposal_count": len(options["company_seeds"]),
            "stage1_proposal_count": stage1_count,
            "proposal_count": len(proposals),
            "selected_candidate_pool_revision_ids": [
                str(value) for value in sorted(selected, key=str)
            ],
            "all_review_states": ["proposed"],
            "proposed_exposure_is_inferred": False,
            "candidate_rows_are_deduplicated": False,
        }
        return command, summary

    def _exact_session_revision(
        self,
        *,
        session_id: UUID,
        session_revision_id: UUID,
        as_of_cutoff: date,
        boundary: datetime,
    ) -> tuple[IndustryThesisSessionIdentity, IndustryThesisSessionRevision]:
        revision = self._session.get(
            IndustryThesisSessionRevision, session_revision_id
        )
        if revision is None or revision.session_id != session_id:
            raise _error(
                "industry_thesis_session_revision_not_found",
                "exact route-owned session revision was not found",
            )
        identity = self._session.get(IndustryThesisSessionIdentity, session_id)
        if identity is None or stored_utc(identity.created_recorded_utc) > boundary:
            raise _error(
                "industry_thesis_session_not_found",
                "exact session was not found",
            )
        if not _visible(
            revision.information_cutoff_date,
            revision.recorded_at_utc,
            as_of_cutoff=as_of_cutoff,
            boundary=boundary,
        ):
            raise _error(
                "industry_thesis_not_visible",
                "session revision is outside the requested boundary",
            )
        return identity, revision

    def _scope_values(
        self, revision: IndustryThesisSessionRevision
    ) -> tuple[list[Any], list[Any]]:
        seeds = json_value(revision.seed_companies_json, "seed_companies")
        graph = json_value(revision.draft_graph_json, "draft_graph")
        if not isinstance(seeds, list) or not isinstance(graph, dict):
            raise _error(
                "industry_thesis_graph_incomplete",
                "stored workbench scope is not structured",
            )
        if graph.get("workbench_contract") != WORKBENCH_SCOPE_CONTRACT:
            raise _error(
                "industry_thesis_workflow_invalid",
                "candidate build is available only for the exact Phase 1B scope contract",
            )
        maps = graph.get("exact_industry_map_references")
        if not isinstance(maps, list):
            raise _error(
                "industry_thesis_graph_incomplete",
                "stored map references are incomplete",
            )
        return seeds, maps

    def _company_seeds(
        self,
        revision: IndustryThesisSessionRevision,
        as_of_cutoff: date,
        boundary: datetime,
    ) -> list[dict[str, Any]]:
        seeds, _ = self._scope_values(revision)
        result: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        allowed = {
            "source_kind",
            "exact_id",
            "stock_basic_record_id",
            "listed_instrument_id",
            "label",
            "code",
        }
        for index, item in enumerate(seeds):
            require_keys(
                item,
                allowed,
                allowed,
                field=f"seed_companies[{index}]",
            )
            stock_id = item["stock_basic_record_id"]
            instrument_id = item["listed_instrument_id"]
            if not _exact_one(stock_id, instrument_id):
                raise _error(
                    "industry_thesis_identity_invalid",
                    "each exact company seed requires exactly one persisted identity authority",
                )
            if stock_id is not None:
                if item["source_kind"] != "stock_basic_record":
                    raise _error(
                        "industry_thesis_identity_invalid",
                        "stock seed source kind does not match its exact identity authority",
                    )
                stock = self._session.get(StockBasicRecord, int(stock_id))
                run = (
                    None
                    if stock is None
                    else self._session.get(IngestionRun, stock.ingestion_run_id)
                )
                if (
                    stock is None
                    or run is None
                    or run.status != "succeeded"
                    or run.completed_at is None
                ):
                    raise _error(
                        "industry_thesis_identity_not_found",
                        "exact stock seed was not found",
                    )
                if (
                    run.information_cutoff_date > as_of_cutoff
                    or stored_utc(run.completed_at) > boundary
                ):
                    raise _error(
                        "industry_thesis_later_information",
                        "stock seed exceeds the requested boundary",
                    )
                if str(stock.id) != str(item["exact_id"]):
                    raise _error(
                        "industry_thesis_identity_invalid",
                        "stock seed exact ID does not match",
                    )
                exact_key = ("stock_basic_record", str(stock.id))
                canonical_label = stock.stock_name
                canonical_code = stock.stock_code
            else:
                if item["source_kind"] != "listed_instrument":
                    raise _error(
                        "industry_thesis_identity_invalid",
                        "listed-instrument seed source kind does not match its exact identity authority",
                    )
                instrument_uuid = parse_uuid(
                    instrument_id,
                    "listed_instrument_id",
                )
                instrument = self._session.get(
                    ListedInstrument,
                    instrument_uuid,
                )
                if (
                    instrument is None
                    or stored_utc(instrument.created_at_utc) > boundary
                ):
                    raise _error(
                        "industry_thesis_identity_not_found",
                        "exact listed-instrument seed was not found",
                    )
                visible = self._session.scalar(
                    select(ListedInstrumentRevision)
                    .where(
                        ListedInstrumentRevision.instrument_id == instrument.id,
                        ListedInstrumentRevision.information_cutoff_date
                        <= as_of_cutoff,
                        ListedInstrumentRevision.recorded_at_utc <= boundary,
                    )
                    .order_by(ListedInstrumentRevision.revision_no.desc())
                    .limit(1)
                )
                if (
                    visible is None
                    or str(instrument.id) != str(item["exact_id"])
                ):
                    raise _error(
                        "industry_thesis_identity_not_found",
                        "listed-instrument seed is not visible",
                    )
                exact_key = ("listed_instrument", str(instrument.id))
                canonical_label = visible.canonical_symbol
                canonical_code = visible.canonical_symbol
            if exact_key in seen:
                raise _error(
                    "industry_thesis_duplicate_source",
                    "stored scope contains a duplicate exact company seed",
                )
            seen.add(exact_key)
            result.append(
                {
                    "source_kind": exact_key[0],
                    "exact_id": exact_key[1],
                    "stock_basic_record_id": (
                        None if stock_id is None else int(stock_id)
                    ),
                    "listed_instrument_id": (
                        None if instrument_id is None else str(instrument_id)
                    ),
                    "label": canonical_label,
                    "code": canonical_code,
                    "selected": True,
                    "selection_owner": "stored_scope_revision",
                }
            )
        result.sort(
            key=lambda item: (
                item["label"].casefold(),
                item["code"].casefold(),
                item["source_kind"],
                item["exact_id"],
            )
        )
        return result

    def _map_source_options(
        self,
        revision: IndustryThesisSessionRevision,
        as_of_cutoff: date,
        boundary: datetime,
    ) -> list[dict[str, Any]]:
        _, references = self._scope_values(revision)
        maps: list[dict[str, Any]] = []
        seen: set[UUID] = set()
        allowed = {
            "source_kind",
            "map_id",
            "map_revision_id",
            "revision_number",
            "title",
        }
        for index, item in enumerate(references):
            require_keys(
                item,
                allowed,
                allowed,
                field=f"exact_industry_map_references[{index}]",
            )
            if item["source_kind"] != "industry_map_revision":
                raise _error(
                    "industry_thesis_source_invalid",
                    "stored Industry Map source kind is invalid",
                )
            map_revision_id = parse_uuid(
                item["map_revision_id"],
                "map_revision_id",
            )
            if map_revision_id in seen:
                raise _error(
                    "industry_thesis_duplicate_source",
                    "stored scope contains a duplicate map revision",
                )
            seen.add(map_revision_id)
            map_revision = self._session.get(
                IndustryMapRevision,
                map_revision_id,
            )
            if (
                map_revision is None
                or str(map_revision.map_id) != str(item["map_id"])
            ):
                raise _error(
                    "industry_thesis_source_not_found",
                    "exact selected Industry Map revision was not found",
                )
            if map_revision.revision_no != int(item["revision_number"]):
                raise _error(
                    "industry_thesis_source_invalid",
                    "stored Industry Map revision number does not match",
                )
            if not _visible(
                map_revision.information_cutoff_date,
                map_revision.recorded_at_utc,
                as_of_cutoff=as_of_cutoff,
                boundary=boundary,
            ):
                raise _error(
                    "industry_thesis_later_information",
                    "Industry Map revision exceeds the requested boundary",
                )
            pools = self._eligible_pools(
                map_revision,
                as_of_cutoff,
                boundary,
            )
            maps.append(
                {
                    "industry_map_id": str(map_revision.map_id),
                    "industry_map_revision_id": str(map_revision.id),
                    "revision_number": map_revision.revision_no,
                    "title": map_revision.title,
                    "scope": map_revision.scope,
                    "eligible_candidate_pool_count": len(pools),
                    "eligible_candidate_pools": pools,
                    "selected_candidate_pool_revision_id": None,
                    "availability_state": (
                        "available" if pools else "no_exact_frozen_pool"
                    ),
                }
            )
        maps.sort(
            key=lambda item: (
                item["title"].casefold(),
                item["industry_map_revision_id"],
            )
        )
        return maps

    def _eligible_pools(
        self,
        map_revision: IndustryMapRevision,
        as_of_cutoff: date,
        boundary: datetime,
    ) -> list[dict[str, Any]]:
        rows = list(
            self._session.execute(
                select(
                    Stage1CandidatePool,
                    Stage1CandidatePoolRevision,
                )
                .join(
                    Stage1CandidatePoolRevision,
                    Stage1CandidatePoolRevision.candidate_pool_id
                    == Stage1CandidatePool.id,
                )
                .where(
                    Stage1CandidatePool.map_id == map_revision.map_id,
                    Stage1CandidatePool.created_at_utc <= boundary,
                    Stage1CandidatePoolRevision.selected_map_revision_id
                    == map_revision.id,
                    Stage1CandidatePoolRevision.information_cutoff_date
                    <= as_of_cutoff,
                    Stage1CandidatePoolRevision.recorded_at_utc <= boundary,
                )
                .order_by(
                    Stage1CandidatePool.pool_key,
                    Stage1CandidatePoolRevision.revision_no,
                    Stage1CandidatePoolRevision.id,
                )
            ).all()
        )
        result: list[dict[str, Any]] = []
        for pool, pool_revision in rows:
            members = self._pool_members(
                pool_revision_id=pool_revision.id,
                map_revision_id=map_revision.id,
                as_of_cutoff=as_of_cutoff,
                boundary=boundary,
            )
            result.append(
                {
                    "candidate_pool_id": str(pool.id),
                    "candidate_pool_revision_id": str(pool_revision.id),
                    "industry_map_revision_id": str(map_revision.id),
                    "pool_key": pool.pool_key,
                    "revision_number": pool_revision.revision_no,
                    "title": pool_revision.title,
                    "scope": pool_revision.scope,
                    "member_count": len(members),
                    "information_cutoff_date": (
                        pool_revision.information_cutoff_date.isoformat()
                    ),
                    "recorded_at_utc": stored_utc(
                        pool_revision.recorded_at_utc
                    ).isoformat(),
                    "selected": False,
                }
            )
        return result

    def _pool_members(
        self,
        *,
        pool_revision_id: UUID,
        map_revision_id: UUID,
        as_of_cutoff: date,
        boundary: datetime,
    ) -> list[dict[str, Any]]:
        pool_revision = self._session.get(
            Stage1CandidatePoolRevision,
            pool_revision_id,
        )
        map_revision = self._session.get(
            IndustryMapRevision,
            map_revision_id,
        )
        if pool_revision is None or map_revision is None:
            raise _error(
                "industry_thesis_source_not_found",
                "exact frozen candidate-pool source was not found",
            )
        pool = self._session.get(
            Stage1CandidatePool,
            pool_revision.candidate_pool_id,
        )
        if (
            pool is None
            or pool.map_id != map_revision.map_id
            or pool_revision.selected_map_revision_id != map_revision.id
        ):
            raise _error(
                "industry_thesis_source_invalid",
                "candidate pool is not bound to the selected map revision",
            )
        if stored_utc(pool.created_at_utc) > boundary:
            raise _error(
                "industry_thesis_later_information",
                "candidate pool identity exceeds the requested boundary",
            )
        if not _visible(
            pool_revision.information_cutoff_date,
            pool_revision.recorded_at_utc,
            as_of_cutoff=as_of_cutoff,
            boundary=boundary,
        ):
            raise _error(
                "industry_thesis_later_information",
                "candidate-pool revision exceeds the requested boundary",
            )
        memberships = list(
            self._session.scalars(
                select(Stage1CandidatePoolMembership)
                .where(
                    Stage1CandidatePoolMembership.candidate_pool_revision_id
                    == pool_revision.id,
                    Stage1CandidatePoolMembership.recorded_at_utc <= boundary,
                )
                .order_by(Stage1CandidatePoolMembership.id)
            )
        )
        result: list[dict[str, Any]] = []
        for membership in memberships:
            revision = self._session.get(
                Stage1BeneficiaryRevision,
                membership.beneficiary_revision_id,
            )
            beneficiary = self._session.get(
                Stage1Beneficiary,
                membership.beneficiary_id,
            )
            if (
                revision is None
                or beneficiary is None
                or revision.beneficiary_id != beneficiary.id
            ):
                raise _error(
                    "industry_thesis_graph_incomplete",
                    "frozen Stage 1 membership graph is incomplete",
                )
            if (
                revision.selected_map_revision_id != map_revision.id
                or beneficiary.map_id != map_revision.map_id
            ):
                raise _error(
                    "industry_thesis_source_invalid",
                    "Stage 1 beneficiary is not bound to the exact map revision",
                )
            if revision.assessment_status != "supported":
                raise _error(
                    "industry_thesis_source_invalid",
                    "frozen candidate-pool member is not a supported Stage 1 revision",
                )
            if not _visible(
                revision.information_cutoff_date,
                revision.recorded_at_utc,
                as_of_cutoff=as_of_cutoff,
                boundary=boundary,
            ):
                raise _error(
                    "industry_thesis_later_information",
                    "Stage 1 beneficiary revision exceeds the requested boundary",
                )
            stock = self._session.get(
                StockBasicRecord,
                revision.stock_basic_record_id,
            )
            run = (
                None
                if stock is None
                else self._session.get(IngestionRun, stock.ingestion_run_id)
            )
            if (
                stock is None
                or run is None
                or run.status != "succeeded"
                or run.completed_at is None
            ):
                raise _error(
                    "industry_thesis_identity_not_found",
                    "Stage 1 company snapshot was not found",
                )
            if (
                stock.source != beneficiary.source
                or stock.stock_code != beneficiary.stock_code
            ):
                raise _error(
                    "industry_thesis_identity_invalid",
                    "Stage 1 company snapshot does not match beneficiary identity",
                )
            if (
                run.information_cutoff_date > as_of_cutoff
                or stored_utc(run.completed_at) > boundary
            ):
                raise _error(
                    "industry_thesis_later_information",
                    "Stage 1 company snapshot exceeds the requested boundary",
                )
            result.append(
                {
                    "industry_map_revision_id": str(map_revision.id),
                    "candidate_pool_revision_id": str(pool_revision.id),
                    "candidate_pool_membership_id": str(membership.id),
                    "stage1_beneficiary_revision_id": str(revision.id),
                    "stage1_beneficiary_id": str(beneficiary.id),
                    "stock_basic_record_id": stock.id,
                    "company_label": stock.stock_name,
                    "stock_code": stock.stock_code,
                    "beneficiary_kind": revision.beneficiary_kind,
                    "rationale_summary": revision.rationale_summary,
                }
            )
        result.sort(
            key=lambda item: (
                item["beneficiary_kind"],
                item["stock_code"],
                item["candidate_pool_membership_id"],
            )
        )
        return result

    @staticmethod
    def _seed_proposal(
        seed: dict[str, Any],
        session_revision_id: UUID,
    ) -> dict[str, Any]:
        proposal = {
            "source_kind": "user_seed",
            "source_reference": {
                "session_revision_id": str(session_revision_id),
                "seed_source_kind": seed["source_kind"],
                "exact_identity_id": seed["exact_id"],
            },
            "company_label_original": seed["label"],
            "benefit_path_text": (
                "该公司由用户在研究范围确认时明确选择为精确公司种子；"
                "尚未审阅其受益路径。"
            ),
            "proposed_exposure_type": "unknown",
            "proposal_confidence": "unknown",
            "identity_state": "exact_accepted_identity",
            "review_state": "proposed",
            "rationale": {
                "kind": "explicit_user_seed",
                "stock_code": seed["code"],
                "statement": "用户明确选择的本地精确公司身份。",
            },
            "uncertainty": {
                "benefit_path": "not_reviewed",
                "typed_exposure": "not_reviewed",
            },
        }
        if seed["stock_basic_record_id"] is not None:
            proposal["proposed_stock_basic_record_id"] = seed[
                "stock_basic_record_id"
            ]
        else:
            proposal["proposed_listed_instrument_id"] = seed[
                "listed_instrument_id"
            ]
        return proposal

    @staticmethod
    def _stage1_proposal(member: dict[str, Any]) -> dict[str, Any]:
        return {
            "source_kind": "existing_industry_map_revision",
            "source_reference": {
                key: member[key]
                for key in (
                    "industry_map_revision_id",
                    "candidate_pool_revision_id",
                    "candidate_pool_membership_id",
                    "stage1_beneficiary_revision_id",
                )
            },
            "proposed_stock_basic_record_id": member[
                "stock_basic_record_id"
            ],
            "company_label_original": member["company_label"],
            "industry_position": (
                f"stage1_beneficiary_kind:{member['beneficiary_kind']}"
            ),
            "benefit_path_text": member["rationale_summary"],
            "proposed_exposure_type": "unknown",
            "proposal_confidence": "unknown",
            "identity_state": "exact_accepted_identity",
            "review_state": "proposed",
            "rationale": {
                "kind": "frozen_stage1_candidate_pool_membership",
                "stock_code": member["stock_code"],
                "stage1_beneficiary_kind": member["beneficiary_kind"],
                "rationale_summary": member["rationale_summary"],
            },
            "uncertainty": {
                "typed_exposure": "not_reviewed",
                "proposal_confidence": "not_assigned",
            },
        }


class IndustryThesisWorkbenchCandidateCommandService(
    IndustryThesisCommandService
):
    """Reuse accepted candidate transactions while strengthening Stage 1 source validation."""

    @staticmethod
    def _validate_candidate_source(
        session: Session,
        proposal: dict[str, Any],
        cutoff: date,
        recorded_at: datetime,
    ) -> None:
        if proposal["source_kind"] != "existing_industry_map_revision":
            IndustryThesisCommandService._validate_candidate_source(
                session,
                proposal,
                cutoff,
                recorded_at,
            )
            return
        if proposal["identity_state"] != "exact_accepted_identity":
            raise _error(
                "industry_thesis_identity_invalid",
                "frozen Stage 1 source requires exact identity",
            )
        stock_id = proposal["proposed_stock_basic_record_id"]
        if (
            stock_id is None
            or proposal["proposed_listed_instrument_id"] is not None
        ):
            raise _error(
                "industry_thesis_identity_invalid",
                "frozen Stage 1 source requires one exact stock identity",
            )
        source_reference = json_value(
            proposal["source_reference_json"],
            "source_reference",
        )
        require_keys(
            source_reference,
            _STAGE1_SOURCE_KEYS,
            _STAGE1_SOURCE_KEYS,
            field="source_reference",
        )
        map_revision = session.get(
            IndustryMapRevision,
            parse_uuid(
                source_reference["industry_map_revision_id"],
                "industry_map_revision_id",
            ),
        )
        pool_revision = session.get(
            Stage1CandidatePoolRevision,
            parse_uuid(
                source_reference["candidate_pool_revision_id"],
                "candidate_pool_revision_id",
            ),
        )
        membership = session.get(
            Stage1CandidatePoolMembership,
            parse_uuid(
                source_reference["candidate_pool_membership_id"],
                "candidate_pool_membership_id",
            ),
        )
        beneficiary_revision = session.get(
            Stage1BeneficiaryRevision,
            parse_uuid(
                source_reference["stage1_beneficiary_revision_id"],
                "stage1_beneficiary_revision_id",
            ),
        )
        if any(
            value is None
            for value in (
                map_revision,
                pool_revision,
                membership,
                beneficiary_revision,
            )
        ):
            raise _error(
                "industry_thesis_source_not_found",
                "exact frozen Stage 1 source graph was not found",
            )
        pool = session.get(
            Stage1CandidatePool,
            pool_revision.candidate_pool_id,
        )
        beneficiary = session.get(
            Stage1Beneficiary,
            beneficiary_revision.beneficiary_id,
        )
        stock = session.get(StockBasicRecord, int(stock_id))
        run = (
            None
            if stock is None
            else session.get(IngestionRun, stock.ingestion_run_id)
        )
        if (
            pool is None
            or beneficiary is None
            or stock is None
            or run is None
            or run.status != "succeeded"
            or run.completed_at is None
        ):
            raise _error(
                "industry_thesis_graph_incomplete",
                "exact frozen Stage 1 source graph is incomplete",
            )
        if (
            pool_revision.selected_map_revision_id != map_revision.id
            or pool.map_id != map_revision.map_id
            or membership.candidate_pool_revision_id != pool_revision.id
            or membership.beneficiary_revision_id != beneficiary_revision.id
            or membership.beneficiary_id != beneficiary.id
            or beneficiary_revision.selected_map_revision_id
            != map_revision.id
            or beneficiary.map_id != map_revision.map_id
            or beneficiary_revision.stock_basic_record_id != stock.id
            or beneficiary.source != stock.source
            or beneficiary.stock_code != stock.stock_code
        ):
            raise _error(
                "industry_thesis_source_invalid",
                "exact frozen Stage 1 source bindings do not match",
            )
        if beneficiary_revision.assessment_status != "supported":
            raise _error(
                "industry_thesis_source_invalid",
                "frozen Stage 1 candidate is not supported",
            )
        dated_rows = (
            (
                map_revision.information_cutoff_date,
                map_revision.recorded_at_utc,
            ),
            (
                pool_revision.information_cutoff_date,
                pool_revision.recorded_at_utc,
            ),
            (
                beneficiary_revision.information_cutoff_date,
                beneficiary_revision.recorded_at_utc,
            ),
            (run.information_cutoff_date, run.completed_at),
        )
        if any(
            item_cutoff > cutoff
            or stored_utc(item_recorded) > recorded_at
            for item_cutoff, item_recorded in dated_rows
        ):
            raise _error(
                "industry_thesis_later_information",
                "frozen Stage 1 source exceeds the thesis boundary",
            )
        if (
            stored_utc(pool.created_at_utc) > recorded_at
            or stored_utc(membership.recorded_at_utc) > recorded_at
        ):
            raise _error(
                "industry_thesis_later_information",
                "frozen Stage 1 pool identity or membership exceeds the thesis boundary",
            )
