import Link from "next/link";
import styles from "../../sign-in/sign-in.module.css";

type SearchParams = Promise<{ token?: string; error?: string }>;

export default async function ResetPasswordPage({ searchParams }: { searchParams: SearchParams }) {
  const { token = "", error } = await searchParams;
  return <main className={styles.page}><section className={styles.brandPanel}><Link className={styles.brand} href="/">MONTAGE</Link><div><h1 className={styles.word}>RETURN.</h1><p className={styles.caption}>Choose a new password without changing workspace ownership or project state.</p></div></section><section className={styles.formPanel}><div className={styles.formWrap}><div className={styles.kicker}>Reset password</div><h2 className={styles.title}>Set a new password.</h2>{error ? <p className={styles.error}>That recovery token is invalid or expired.</p> : null}<form className={styles.form} action="/api/auth/recovery/reset" method="post"><input name="token" type="hidden" value={token} /><label className={styles.label}>New password<input className={styles.input} name="password" type="password" autoComplete="new-password" minLength={12} required /></label><button className={styles.button} type="submit">Reset password</button></form><Link className={styles.back} href="/sign-in">← Back to sign in</Link></div></section></main>;
}
