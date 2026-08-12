import { describe, it, expect } from "vitest";
import { OPTIMIZATION_TITLES } from "./NuvemshopAnalise";

/**
 * Regressão: OPTIMIZATION_TITLES não cobria os
 * valores REAIS de optimization_type emitidos por
 * backend/app/integrations/nuvemshop_optimizer.py — resultado, cards de
 * categoria/página/blog mostravam literalmente "Otimização: undefined", e a
 * otimização de nome de produto (optimization_type="title") era rotulada
 * como "Otimização do Título da Página" (rótulo de página, não de produto).
 *
 * Esta lista replica EXATAMENTE os valores que o backend gera (ver
 * nuvemshop_optimizer.py: field_mapping do produto, e os f"category_{field}"
 * / f"page_{field}" / f"blog_{field}" de categoria/página/blog).
 */
const BACKEND_EMITTED_OPTIMIZATION_TYPES = [
  // Produto (sem prefixo)
  "title",
  "description",
  "seo_title",
  "seo_description",
  "tags",
  // Categoria
  "category_title",
  "category_description",
  "category_seo_title",
  "category_seo_description",
  // Página
  "page_title",
  "page_content",
  "page_seo_title",
  "page_seo_description",
  // Blog
  "blog_title",
  "blog_body",
  "blog_seo_title",
  "blog_seo_description",
  "blog_tags",
];

describe("OPTIMIZATION_TITLES (Nuvemshop)", () => {
  it.each(BACKEND_EMITTED_OPTIMIZATION_TYPES)(
    "tem rótulo definido para optimization_type=%s (nunca 'undefined')",
    (key) => {
      const label = OPTIMIZATION_TITLES[key];
      expect(label).toBeDefined();
      expect(label).not.toContain("undefined");
    }
  );

  it("rotula o nome do produto (title) como produto, não como página", () => {
    // "title" (produto) estava mapeado para o rótulo de PÁGINA.
    expect(OPTIMIZATION_TITLES["title"]).toBe("Otimização do Nome do Produto");
    expect(OPTIMIZATION_TITLES["title"]).not.toMatch(/página/i);
  });

  it("distingue título de produto do título de página/categoria/blog", () => {
    const labels = [
      OPTIMIZATION_TITLES["title"],
      OPTIMIZATION_TITLES["category_title"],
      OPTIMIZATION_TITLES["page_title"],
      OPTIMIZATION_TITLES["blog_title"],
    ];
    // Todos definidos e todos distintos entre si
    expect(labels.every(Boolean)).toBe(true);
    expect(new Set(labels).size).toBe(4);
  });
});
