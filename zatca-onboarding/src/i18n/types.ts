/**
 * A message is either a plain string or, when it varies with a count, one entry
 * per CLDR plural category.
 *
 * English needs two of those categories; Arabic needs six. Modelling the message
 * as an object rather than suffixed keys lets each language declare exactly the
 * forms it uses while still being checked for completeness.
 */
export type PluralForms = Partial<Record<Intl.LDMLPluralRule, string>>;
export type Message = string | PluralForms;

/** Values interpolated into `{placeholders}`. `count` also selects the plural. */
export type Params = Record<string, string | number>;
