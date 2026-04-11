import * as fs from "node:fs";
import * as path from "node:path";
import { generateDynamicSPARQLPrompt } from "./promptGenerator";

const NLP4RE_TEMPLATE_PATH = path.resolve(__dirname, "../templates/nlp4re-template.json");

function readJsonFile<T>(filePath: string): T {
	const fileContent = fs.readFileSync(filePath, "utf-8");
  	return JSON.parse(fileContent) as T;
}



function main(): void {
    const templateMapping = readJsonFile<Record<string, unknown>>(NLP4RE_TEMPLATE_PATH);


	const prompt = generateDynamicSPARQLPrompt(
		templateMapping as any,
		"R1544125",
		"NLP for Requirements Engineering (NLP4RE)",
		"C121001"
	);

	console.log("Prompt generated successfully.");
	console.log(`Template file: ${NLP4RE_TEMPLATE_PATH}`);
	console.log(`Prompt length: ${prompt.length}`);
	console.log("");
	console.log(prompt);
}

main();