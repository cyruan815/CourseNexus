import { Alert, Anchor, Box, Button, PasswordInput, Stack, Text, TextInput, Title } from "@mantine/core";
import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { login, register } from "./api";
import { WelcomeParticleCanvas } from "./WelcomeParticleCanvas";
import "./auth-pages.css";

type AuthMode = "login" | "register";

interface AuthFormState {
  nickname: string;
  password: string;
  username: string;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "认证请求失败，请稍后重试";
}

function AuthArt({ mode }: { mode: AuthMode }) {
  const isLogin = mode === "login";

  return (
    <aside className="auth-art" aria-label={isLogin ? "登录视觉区" : "注册视觉区"}>
      <Anchor className="auth-art__home" component={Link} to="/welcome">
        CourseNexus
      </Anchor>
      <Box className="auth-art__copy">
        <Text className="auth-art__kicker">{isLogin ? "Morning study desk" : "First course setup"}</Text>
        <Title order={2}>{isLogin ? "整理资料，开始学习。" : "创建账号，建立第一门课程。"}</Title>
        <Text>
          {isLogin
            ? "登录后进入课程首页，继续上传资料、选择资料范围，并开始智能体对话。"
            : "注册后进入系统首页，从课程创建开始，把分散资料放进同一个工作台。"}
        </Text>
      </Box>
    </aside>
  );
}

function AuthForm({ mode }: { mode: AuthMode }) {
  const navigate = useNavigate();
  const isLogin = mode === "login";
  const [values, setValues] = useState<AuthFormState>({
    nickname: "",
    password: "",
    username: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function updateField(field: keyof AuthFormState, value: string) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      if (isLogin) {
        await login({ username: values.username, password: values.password });
      } else {
        await register({
          username: values.username,
          password: values.password,
          nickname: values.nickname.trim() || null,
        });
      }

      navigate("/");
    } catch (submitError) {
      setError(getErrorMessage(submitError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-form-area">
      <Box className="auth-form-card">
        <Title order={1}>{isLogin ? "登录 CourseNexus" : "注册 CourseNexus"}</Title>
        <Text className="auth-form-card__copy">
          {isLogin ? "使用用户名或邮箱进入学习工作台。" : "创建账号后进入系统首页。"}
        </Text>

        {error ? (
          <Alert color="red" role="alert" title={isLogin ? "登录失败" : "注册失败"}>
            {error}
          </Alert>
        ) : null}

        <form aria-label={isLogin ? "登录表单" : "注册表单"} onSubmit={handleSubmit}>
          <Stack gap="lg">
            {isLogin ? null : (
              <TextInput
                autoComplete="name"
                label="昵称"
                name="nickname"
                onChange={(event) => updateField("nickname", event.currentTarget.value)}
                placeholder="请输入昵称"
                value={values.nickname}
              />
            )}
            <TextInput
              autoComplete="username"
              label="用户名/邮箱"
              name="username"
              onChange={(event) => updateField("username", event.currentTarget.value)}
              placeholder="请输入用户名或邮箱"
              required
              value={values.username}
            />
            <PasswordInput
              autoComplete={isLogin ? "current-password" : "new-password"}
              label="密码"
              name="password"
              onChange={(event) => updateField("password", event.currentTarget.value)}
              placeholder="请输入密码"
              required
              value={values.password}
            />

            <Box className="auth-form-row">
              {isLogin ? (
                <Text span>
                  没有账户？{" "}
                  <Anchor component={Link} to="/register">
                    点击注册
                  </Anchor>
                </Text>
              ) : (
                <>
                  <Text span>
                    已有账户？{" "}
                    <Anchor component={Link} to="/login">
                      去登录
                    </Anchor>
                  </Text>
                  <Text span>注册后进入首页</Text>
                </>
              )}
            </Box>

            <Button loading={isSubmitting} type="submit">
              {isLogin ? "登录" : "注册"}
            </Button>
          </Stack>
        </form>
      </Box>
    </main>
  );
}

export function WelcomeAuthPage() {
  return (
    <main className="auth-welcome">
      <WelcomeParticleCanvas />
      <header className="auth-welcome__nav">
        <Anchor aria-label="CourseNexus 首页" className="auth-wordmark" component={Link} to="/welcome">
          <img alt="" src="/brand/coursenexus-logo.png" />
        </Anchor>
        <nav aria-label="入口导航">
          <Anchor className="active" component={Link} to="/welcome">
            主页
          </Anchor>
          <Anchor component={Link} to="/login">
            登录
          </Anchor>
          <Anchor component={Link} to="/register">
            注册
          </Anchor>
          <Anchor component={Link} to="/login">
            进入工作台
          </Anchor>
        </nav>
      </header>

      <section className="auth-welcome__main" aria-labelledby="welcome-title">
        <Box>
          <Title id="welcome-title" order={1}>
            <img alt="" className="auth-hero-logo" src="/brand/coursenexus-logo.png" />
            <span>课枢</span>
          </Title>
          <Title order={2}>你的多课程 AI 学习工作台</Title>
          <Text>
            把课程资料、问答、生成内容和学习计划组织成清晰、可追踪、可执行的学习路径。
          </Text>
          <Button component={Link} to="/login">
            开始
          </Button>
        </Box>
      </section>
    </main>
  );
}

export function LoginAuthPage() {
  return (
    <section className="auth-page">
      <AuthArt mode="login" />
      <AuthForm mode="login" />
    </section>
  );
}

export function RegisterAuthPage() {
  return (
    <section className="auth-page">
      <AuthArt mode="register" />
      <AuthForm mode="register" />
    </section>
  );
}
