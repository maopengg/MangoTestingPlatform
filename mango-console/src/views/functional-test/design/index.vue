<template>
  <TableBody>
    <template #header>
      <TableHeader :title="developmentDesignPage.title" />
    </template>

    <template #default>
      <section class="mango-section-card mango-development-design">
        <div class="mango-section-title">
          <div class="mango-section-title__main">
            <h2>{{ developmentDesignPage.title }}</h2>
            <p>{{ developmentDesignPage.description }}</p>
          </div>
        </div>
        <div class="mango-empty-state mango-development-design__empty">
          {{ developmentDesignPage.emptyText }}
        </div>
      </section>
    </template>
  </TableBody>
</template>

<script setup lang="ts">
  import { developmentDesignPage } from './config'
</script>

<style scoped lang="less">
  .mango-development-design {
    min-height: 240px;
  }

  .mango-development-design__empty {
    min-height: 160px;
  }
</style>
