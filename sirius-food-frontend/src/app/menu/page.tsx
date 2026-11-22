import type { Metadata } from "next";

import { DishCard } from "@/components/DishCard";
import { getMenuItems } from "@/lib/api";

export const metadata: Metadata = {
  title: "Меню",
  description: "Витрина «Сириус.Еды»: блюда кампуса из REST API.",
};

// Готовый HTML списка хранится 60 секунд (ISR).
export const revalidate = 60;

export default async function MenuPage() {
  const items = await getMenuItems();

  return (
    <main className="page-shell">
      <section className="menu-section" id="menu">
        <div className="section-heading">
          <div>
            <p className="eyebrow">
              <span className="eyebrow-dot" />
              Меню
            </p>
            <h2>
              Меню<span className="heading-period">.</span>
            </h2>
            <p className="section-description">Данные отрендерены на сервере.</p>
          </div>
          <div className="menu-count">
            <strong>{items.length}</strong>
            <span>блюд в витрине</span>
          </div>
        </div>
        <div className="dish-grid">
          {items.map((item) => (
            <DishCard key={item.id} item={item} />
          ))}
        </div>
      </section>
    </main>
  );
}
