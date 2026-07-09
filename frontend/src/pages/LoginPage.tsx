export function LoginPage() {
  return (
    <main>
      <p>CourseNexus</p>
      <h1>登录 CourseNexus</h1>
      <form aria-label="登录表单">
        <label>
          邮箱
          <input autoComplete="email" name="email" type="email" />
        </label>
        <label>
          密码
          <input autoComplete="current-password" name="password" type="password" />
        </label>
        <button type="submit">登录</button>
      </form>
    </main>
  );
}
