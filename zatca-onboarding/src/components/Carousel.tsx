import React, { useEffect, useState } from "react";

const Carousel: React.FC = () => {
  const items = [
    {
      id: 1,
      src: "https://fakeimg.pl/1350x600/cccfd4/000000?text=1&font=bebas",
    },
    {
      id: 2,
      src: "https://fakeimg.pl/1350x600/cccfd4/000000?text=2&font=bebas",
    },
    {
      id: 3,
      src: "https://fakeimg.pl/1350x600/cccfd4/000000?text=3&font=bebas",
    },
    {
      id: 4,
      src: "https://fakeimg.pl/1350x600/cccfd4/000000?text=4&font=bebas",
    },
  ];

  const [currentIndex, setCurrentIndex] = useState(0);

  // Automatic slide change every 5 seconds
  useEffect(() => {
    const intervalId = setInterval(() => {
      setCurrentIndex((prevIndex) => (prevIndex + 1) % items.length);
    }, 5000);

    return () => clearInterval(intervalId);
  }, []);

  const handleDotClick = (index: number) => {
    setCurrentIndex(index);
  };

  return (
    <div className="relative w-full h-full">
      <div className="relative w-full h-full overflow-hidden">
        <div
          className="flex transition-transform duration-1000 ease-in-out"
          style={{ transform: `translateX(-${currentIndex * 100}%)` }}
        >
          {items.map((item) => (
            <div className="w-full flex-shrink-0" key={item.id}>
              <img
                src={item.src}
                className="w-full max-h-[450px] object-cover"
                alt={`carousel-item-${item.id}`}
              />
            </div>
          ))}
        </div>
      </div>

      <div className="absolute bottom-5 left-1/2 transform -translate-x-1/2 flex space-x-2">
        {items.map((_, index) => (
          <button
            key={index}
            onClick={() => handleDotClick(index)}
            className={`w-3 h-3 rounded-full border-solid border-black ${
              index === currentIndex ? "bg-white" : "bg-[#483f61]"
            } border border-white`}
          ></button>
        ))}
      </div>
    </div>
  );
};

export default Carousel;
