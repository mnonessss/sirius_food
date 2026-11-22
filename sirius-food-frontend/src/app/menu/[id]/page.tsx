import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { DishArtwork } from "@/components/DishArtwork";
import { formatPrice, getMenuItem, getMenuItems } from "@/lib/api";
import { presentDish } from "@/lib/presentation";

type PageProps = {
  params: Promise<{ id: string }>;
};

// Карточка тоже обновляется не чаще раза в минуту.
export const revalidate = 60;

export async function generateStaticParams() {
  const items = await getMenuItems();
  return items.map((item) => ({ id: String(item.id) }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const item = await getMenuItem(id);

  if (!item) {
    return { title: "Блюдо не найдено" };
  }

  const description = `${item.name} за ${formatPrice(item.price)} в меню кампуса «Сириус.Еда».`;

  return {
    title: item.name,
    description,
    openGraph: {
      title: item.name,
      description,
      type: "article",
    },
  };
}

export default async function MenuItemPage({ params }: PageProps) {
  const { id } = await params;
  const item = await getMenuItem(id);

  if (!item) notFound();

  const art = presentDish(item);
  const category = item.category ?? "Меню";

  return (
    <main className="page-shell detail-page">
      <div className="breadcrumbs">
        <Link href="/menu">Меню</Link>
        <span aria-hidden="true">/</span>
        <span>{item.name}</span>
      </div>
      <article className="detail-card">
        <div className="detail-card__art">
          <DishArtwork emoji={art.emoji} tone={art.tone} category={category} />
          <span className="detail-card__art-caption">#{item.id}</span>
        </div>
        <div className="detail-card__info">
          <p className="eyebrow">
            <span className="eyebrow-dot" />
            {category}
          </p>
          <h1>{item.name}</h1>
          <p className="detail-card__description">
            Карточка собрана на сервере из REST API.
          </p>
          <div className="detail-price-row">
            <div>
              <span className="detail-price-label">Цена</span>
              <strong className="detail-price">{formatPrice(item.price)}</strong>
            </div>
            <span className="availability">
              <i />В наличии
            </span>
          </div>
        </div>
      </article>
      <Link className="back-link" href="/menu">
        ← Назад к меню
      </Link>
    </main>
  );
}
