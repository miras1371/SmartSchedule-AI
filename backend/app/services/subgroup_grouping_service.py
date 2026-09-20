from collections.abc import Sequence

from backend.app.models.subgroup import Subgroup


def group_subgroups(
    subgroups: Sequence[Subgroup],
    max_students: int | None,
) -> list[list[Subgroup]]:
    """Pack subgroups as close as possible to the configured limit."""
    if max_students is None:
        return [[subgroup] for subgroup in subgroups]

    if max_students <= 0:
        raise ValueError(
            "Максимальный размер объединения должен быть больше нуля."
        )

    remaining = list(subgroups)
    result: list[list[Subgroup]] = []

    for subgroup in remaining:
        subgroup_size = subgroup.student_count
        if subgroup.student_count > max_students:
            raise ValueError(
                f"Подгруппа «{subgroup.name}» содержит "
                f"{subgroup_size} студентов, что превышает лимит "
                f"{max_students}."
            )

    while remaining:
        best_indexes: tuple[int, ...] = ()
        best_total = 0

        def search(
            start: int,
            total: int,
            indexes: tuple[int, ...],
        ) -> None:
            nonlocal best_total, best_indexes

            if total > best_total:
                best_total = total
                best_indexes = indexes

            for index in range(start, len(remaining)):
                next_total = total + remaining[index].student_count
                if next_total <= max_students:
                    search(
                        index + 1,
                        next_total,
                        indexes + (index,),
                    )

        search(0, 0, ())

        selected = set(best_indexes)
        result.append(
            [subgroup for index, subgroup in enumerate(remaining)
             if index in selected]
        )
        remaining = [
            subgroup
            for index, subgroup in enumerate(remaining)
            if index not in selected
        ]

    return result
