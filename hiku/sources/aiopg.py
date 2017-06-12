from __future__ import absolute_import

from . import sqlalchemy as _sa


class FieldsQuery(_sa.FieldsQuery):

    async def __call__(self, ctx, fields_, ids):
        if not ids:
            return []

        expr, result_proc = self.__select_expr__(fields_, ids)

        sa_engine = ctx[self.sa_engine_ctx_var]
        async with sa_engine.acquire() as connection:
            res = await connection.execute(expr)
            rows = await res.fetchall()

        return result_proc(rows)


class AsyncLinkQueryMixin:

    async def __call__(self, ctx, ids):
        expr = self.__select_expr__(ids)
        if expr is None:
            pairs = []
        else:
            sa_engine = ctx[self.sa_engine_ctx_var]
            async with sa_engine.acquire() as connection:
                res = await connection.execute(expr)
                rows = await res.fetchall()
            pairs = [(r.from_column, r.to_column) for r in rows]
        return self.__result_proc__(pairs, ids)


class LinkOneQuery(AsyncLinkQueryMixin, _sa.LinkOneQuery):
    pass


class LinkOptionalQuery(AsyncLinkQueryMixin, _sa.LinkOptionalQuery):
    pass


class LinkSequenceQuery(AsyncLinkQueryMixin, _sa.LinkSequenceQuery):
    pass
