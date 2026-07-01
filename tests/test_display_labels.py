from src.display_labels import (
    get_operation_mode,
    get_metric_label,
    get_strategy_group,
    get_strategy_label,
    get_strategy_short_description,
)


def test_o1_o2_o3_return_distinct_labels() -> None:
    labels = {
        get_strategy_label("O1_TARGET_HOLD_BUFFER"),
        get_strategy_label("O2_STRETCH_TARGET_CAPTURE"),
        get_strategy_label("O3_QUALITY_GUARD_RELIEF"),
    }

    assert labels == {"버퍼 유지", "Stretch 전환", "품질 방어"}


def test_under_on_over_operation_modes_are_distinct() -> None:
    assert get_operation_mode("UNDER_TARGET") == "목표 보정 필요"
    assert get_operation_mode("ON_TARGET") == "유지/모니터링"
    assert get_operation_mode("OVER_TARGET") == "초과달성 관리"
    assert len(
        {
            get_operation_mode("UNDER_TARGET"),
            get_operation_mode("ON_TARGET"),
            get_operation_mode("OVER_TARGET"),
        }
    ) == 3


def test_next_close_required_metric_label_is_cumulative_line_copy() -> None:
    assert get_metric_label("next_close_required_amount") == "다음 마감 누적선 필요실적"


def test_strategy_groups_and_descriptions_are_business_facing() -> None:
    assert get_strategy_group("P1_ALL_REMAINING") == "목표 보정"
    assert get_strategy_group("O2_STRETCH_TARGET_CAPTURE") == "초과달성 운영"
    assert "취소/철회/미결제" in get_strategy_short_description("O3_QUALITY_GUARD_RELIEF")
