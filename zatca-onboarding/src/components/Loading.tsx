import { LoadingOutlined } from "@ant-design/icons"
import { Flex, Spin } from "antd"

const Loading: React.FC = () => {
  return (
<Flex align="center" justify="center" className="h-full">
  <Spin indicator={<LoadingOutlined spin />} size="large" />
</Flex>
  )
}

export default Loading