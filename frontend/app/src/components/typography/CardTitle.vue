<script setup lang="ts">
const { dark } = useTheme();
</script>

<template>
  <div
    class="card-title"
    :class="{
      [$style.title]: true,
      [$style.dark]: dark
    }"
  >
    <slot />
  </div>
</template>

<style module lang="scss">
.title {
  font-size: 14px;
  line-height: 17px;
  /* identical to box height */

  text-transform: uppercase;

  color: #447178;
  height: 24px;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.dark {
  color: #62a4af;
}
</style>
