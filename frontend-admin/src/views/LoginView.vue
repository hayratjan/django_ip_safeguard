<template>
  <div style="display: flex; height: 100%; align-items: center; justify-content: center; background: #f4f6f8">
    <el-card style="width: 360px">
      <h3>企业控制台登录</h3>
      <el-form :model="form" label-position="top">
        <el-form-item label="用户名">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-button type="primary" :loading="loading" style="width: 100%" @click="onLogin">登录</el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { useRouter } from "vue-router";
import { getCsrf, loginApi } from "../api";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const store = useAuthStore();
const loading = ref(false);
const form = reactive({ username: "", password: "" });

const onLogin = async () => {
  loading.value = true;
  try {
    await getCsrf();
    await loginApi(form);
    await store.fetchMe();
    ElMessage.success("登录成功");
    router.push("/dashboard");
  } finally {
    loading.value = false;
  }
};
</script>
