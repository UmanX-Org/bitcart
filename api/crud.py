# pylint: disable=no-member
from typing import Iterable, Union

import asyncpg
from fastapi import Depends, HTTPException

from . import models, pagination, schemes, tasks, utils, settings
from .db import db


async def user_count():
    return await db.func.count(models.User.id).gino.scalar()


async def create_user(user: schemes.CreateUser):
    count = await user_count()
    return await models.User.create(
        username=user.username,
        hashed_password=utils.get_password_hash(user.password),
        email=user.email,
        is_superuser=True if count == 0 else False,
    )


async def create_invoice(invoice: schemes.CreateInvoice):
    d = invoice.dict()
    products = d.get("products")
    obj, xpub = await models.Invoice.create(**d)
    created = []
    for i in products:  # type: ignore
        created.append(
            (
                await models.ProductxInvoice.create(invoice_id=obj.id, product_id=i)
            ).product_id
        )
    obj.products = created
    tasks.poll_updates.send(obj.id, xpub, settings.TEST)
    return obj


async def invoice_add_related(item: models.Invoice):
    # add related products
    result = (
        await models.ProductxInvoice.select("product_id")
        .where(models.ProductxInvoice.invoice_id == item.id)
        .gino.all()
    )
    item.products = [product_id for product_id, in result if product_id]


async def invoices_add_related(items: Iterable[models.Invoice]):
    for item in items:
        await invoice_add_related(item)
    return items


async def get_invoice(model_id: Union[int, str]):
    try:
        item = await models.Invoice.get(model_id)
    except asyncpg.exceptions.DataError as e:
        raise HTTPException(422, e.message)
    if not item:
        raise HTTPException(
            status_code=404, detail=f"Object with id {model_id} does not exist!"
        )
    await invoice_add_related(item)
    return item


async def get_invoices(pagination: pagination.Pagination = Depends()):
    return await pagination.paginate(models.Invoice, postprocess=invoices_add_related)


async def delete_invoice(model_id: int):
    item = await get_invoice(model_id)
    await invoice_add_related(item)
    await models.ProductxInvoice.delete.where(
        models.ProductxInvoice.invoice_id == item.id
    ).gino.status()
    await item.delete()
    return item
