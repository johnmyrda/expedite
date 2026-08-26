"""Order repository."""

from sqlmodel import Session, select

from expedite.models import OrderLineRecord, OrderRecord
from expedite.storage.repositories.base import Repository


class OrderRepository(Repository[OrderRecord]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, OrderRecord)

    def find_all_by_event_id(self, event_id: int) -> list[OrderRecord]:
        return list(
            self.session.exec(select(OrderRecord).where(OrderRecord.event_id == event_id)).all()
        )

    def find_by_event_id_and_order_number(
        self,
        event_id: int,
        order_number: int,
    ) -> OrderRecord | None:
        return self.session.exec(
            select(OrderRecord).where(
                OrderRecord.event_id == event_id,
                OrderRecord.order_id == order_number,
            )
        ).first()

    def replace_line_items(
        self,
        order: OrderRecord,
        line_items: list[OrderLineRecord],
    ) -> None:
        existing_lines = list(order.line_items)
        order.line_items = []
        for line in existing_lines:
            self.session.delete(line)
        self.session.flush()
        order.line_items = line_items
