import { z } from "zod";

// ==============================================
// Validações de Segurança para Autenticação
// ==============================================

// Validação forte de senha
export const passwordSchema = z
  .string()
  .min(8, "Senha deve ter no mínimo 8 caracteres")
  .max(72, "Senha deve ter no máximo 72 caracteres")
  .regex(/[a-z]/, "Senha deve conter pelo menos uma letra minúscula")
  .regex(/[A-Z]/, "Senha deve conter pelo menos uma letra maiúscula")
  .regex(/[0-9]/, "Senha deve conter pelo menos um número")
  .regex(/[^a-zA-Z0-9]/, "Senha deve conter pelo menos um caractere especial");

// Validação de email
export const emailSchema = z
  .string()
  .email("E-mail inválido")
  .min(5, "E-mail inválido")
  .max(255, "E-mail muito longo");

// Schema de login
export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, "Senha é obrigatória"),
});

// Schema de registro
export const registerSchema = z.object({
  email: emailSchema,
  password: passwordSchema,
  inviteCode: z
    .string()
    .min(1, "Código de convite é obrigatório")
    .max(50, "Código de convite inválido"),
});

// Schema de reset de senha
export const resetPasswordSchema = z.object({
  email: emailSchema,
});

// Schema de nova senha
export const newPasswordSchema = z.object({
  password: passwordSchema,
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Senhas não conferem",
  path: ["confirmPassword"],
});

// ==============================================
// Validações de Sites e SEO
// ==============================================

// Validação de URL
export const urlSchema = z
  .string()
  .url("URL inválida")
  .min(10, "URL muito curta")
  .max(2048, "URL muito longa")
  .refine(
    (url) => url.startsWith("http://") || url.startsWith("https://"),
    "URL deve começar com http:// ou https://"
  );

// Plataformas suportadas
export const platformSchema = z.enum([
  "shopify",
  "lojaintegrada",
  "tray",
  "nuvemshop",
  "vtex",
  "wordpress",
  "magento",
  "outro",
]).optional();

// Schema de criação de site
export const siteCreateSchema = z.object({
  baseUrl: urlSchema,
  platform: platformSchema,
});

// Schema de atualização de site
export const siteUpdateSchema = z.object({
  baseUrl: urlSchema.optional(),
  platform: platformSchema,
  ownerEmail: emailSchema.optional(),
});

// ==============================================
// Tipos inferidos
// ==============================================
export type LoginInput = z.infer<typeof loginSchema>;
export type RegisterInput = z.infer<typeof registerSchema>;
export type ResetPasswordInput = z.infer<typeof resetPasswordSchema>;
export type NewPasswordInput = z.infer<typeof newPasswordSchema>;
export type SiteCreateInput = z.infer<typeof siteCreateSchema>;
export type SiteUpdateInput = z.infer<typeof siteUpdateSchema>;

// ==============================================
// Helpers
// ==============================================

// Helper para extrair erros de validação
export function getValidationErrors(error: z.ZodError): Record<string, string> {
  const errors: Record<string, string> = {};
  error.errors.forEach((err) => {
    const path = err.path.join(".");
    if (!errors[path]) {
      errors[path] = err.message;
    }
  });
  return errors;
}

// Validar força da senha (para UI)
export function getPasswordStrength(password: string): {
  score: number;
  label: string;
  color: string;
} {
  let score = 0;
  
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[a-z]/.test(password)) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^a-zA-Z0-9]/.test(password)) score++;
  
  if (score <= 2) return { score, label: "Fraca", color: "bg-destructive" };
  if (score <= 4) return { score, label: "Média", color: "bg-yellow-500" };
  return { score, label: "Forte", color: "bg-green-500" };
}

// Validar URL de forma síncrona (para UI)
export function isValidUrl(url: string): boolean {
  try {
    urlSchema.parse(url);
    return true;
  } catch {
    return false;
  }
}

// Validar e retornar erro ou null
export function validateSiteCreate(data: unknown): { data: SiteCreateInput } | { error: string } {
  try {
    const parsed = siteCreateSchema.parse(data);
    return { data: parsed };
  } catch (err) {
    if (err instanceof z.ZodError) {
      return { error: err.errors[0]?.message || "Dados inválidos" };
    }
    return { error: "Erro de validação" };
  }
}

export function validateSiteUpdate(data: unknown): { data: SiteUpdateInput } | { error: string } {
  try {
    const parsed = siteUpdateSchema.parse(data);
    return { data: parsed };
  } catch (err) {
    if (err instanceof z.ZodError) {
      return { error: err.errors[0]?.message || "Dados inválidos" };
    }
    return { error: "Erro de validação" };
  }
}
