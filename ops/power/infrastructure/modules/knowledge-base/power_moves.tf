moved {
 from = aws_opensearchserverless_collection.kb
 to = aws_opensearchserverless_collection.kb[0]
}
moved {
 from = null_resource.kb_index_bootstrap
 to = null_resource.kb_index_bootstrap[0]
}
moved {
 from = aws_bedrockagent_knowledge_base.main
 to = aws_bedrockagent_knowledge_base.main[0]
}
moved {
 from = aws_bedrockagent_data_source.s3
 to = aws_bedrockagent_data_source.s3[0]
}
