import * as fs from "node:fs";
import * as path from "node:path";

const NLP4RE_TEMPLATE_PATH = path.resolve(
  __dirname,
  "../templates/nlp4re-template.json"
);

function readJsonFile<T>(filePath: string): T {
  const raw = fs.readFileSync(filePath, "utf-8");
  return JSON.parse(raw) as T;
}

function main(): void {
  const templateMapping = readJsonFile<Record<string, unknown>>(
    NLP4RE_TEMPLATE_PATH
  );

  const predicateIds = Object.keys(templateMapping);

  console.log(`Template file: ${NLP4RE_TEMPLATE_PATH}`);
  console.log(`Loaded predicates: ${predicateIds.length}`);

  if (predicateIds.length > 0) {
    console.log(`First predicate id: ${predicateIds[0]}`);
  }
}

main();