<script setup lang="ts">
import { Module } from '@/types/modules';

const modules = [Module.NFTS];
const { isModuleEnabled } = useModules();
const enabled = isModuleEnabled(modules[0]);
</script>

<template>
  <VContainer>
    <ModuleNotActive v-if="!enabled" :modules="modules" />
    <NftGallery v-else :modules="modules" />
  </VContainer>
</template>
